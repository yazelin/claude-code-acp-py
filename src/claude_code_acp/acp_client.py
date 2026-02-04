"""
ACP Client - Connect to any ACP-compatible agent.

This module provides a client that can connect to any ACP agent
(like claude-code-acp, or Zed's TypeScript version) via subprocess.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Callable, Coroutine

from acp.client.connection import ClientSideConnection
from acp.schema import (
    AgentMessageChunk,
    AgentThoughtChunk,
    Implementation,
    PermissionOption,
    RequestPermissionResponse,
    TextContentBlock,
    ToolCallProgress,
    ToolCallStart,
    ToolCallUpdate,
)

logger = logging.getLogger(__name__)

__all__ = ["AcpClient", "AcpClientEvents"]


@dataclass
class AcpClientEvents:
    """Event handlers for ACP client."""

    on_text: Callable[[str], Coroutine[Any, Any, None]] | None = None
    on_thinking: Callable[[str], Coroutine[Any, Any, None]] | None = None
    on_tool_start: Callable[[str, str, dict], Coroutine[Any, Any, None]] | None = None
    on_tool_end: Callable[[str, str, Any], Coroutine[Any, Any, None]] | None = None
    on_permission: Callable[[str, dict, list], Coroutine[Any, Any, str]] | None = None
    on_error: Callable[[Exception], Coroutine[Any, Any, None]] | None = None
    on_complete: Callable[[], Coroutine[Any, Any, None]] | None = None


class AcpClient:
    """
    ACP Client that connects to any ACP-compatible agent.

    This client spawns an ACP agent as a subprocess and communicates
    via the Agent Client Protocol (JSON-RPC over stdio).

    Example:
        ```python
        # Connect to claude-code-acp
        client = AcpClient(command="claude-code-acp")

        # Or connect to the TypeScript version
        client = AcpClient(command="npx", args=["@anthropic/claude-code-acp"])

        @client.on_text
        async def handle_text(text):
            print(text, end="")

        async with client:
            await client.prompt("Hello!")
        ```
    """

    def __init__(
        self,
        command: str = "claude-code-acp",
        args: list[str] | None = None,
        cwd: str = ".",
        env: dict[str, str] | None = None,
    ):
        """
        Initialize the ACP client.

        Args:
            command: The ACP agent command to run.
            args: Additional arguments for the command.
            cwd: Working directory for the agent.
            env: Additional environment variables.
        """
        self.command = command
        self.args = args or []
        self.cwd = cwd
        self.env = env
        self.events = AcpClientEvents()

        self._process: asyncio.subprocess.Process | None = None
        self._connection: ClientSideConnection | None = None
        self._session_id: str | None = None
        self._text_buffer = ""
        self._initialized = False

    # --- Event decorators ---

    def on_text(self, func: Callable[[str], Coroutine[Any, Any, None]]):
        """Register handler for text responses."""
        self.events.on_text = func
        return func

    def on_thinking(self, func: Callable[[str], Coroutine[Any, Any, None]]):
        """Register handler for thinking blocks."""
        self.events.on_thinking = func
        return func

    def on_tool_start(self, func: Callable[[str, str, dict], Coroutine[Any, Any, None]]):
        """Register handler for tool start events."""
        self.events.on_tool_start = func
        return func

    def on_tool_end(self, func: Callable[[str, str, Any], Coroutine[Any, Any, None]]):
        """Register handler for tool end events."""
        self.events.on_tool_end = func
        return func

    def on_permission(self, func: Callable[[str, dict, list], Coroutine[Any, Any, str]]):
        """
        Register handler for permission requests.

        The handler receives (name, input, options) and should return
        the option_id to select (e.g., "allow", "reject", "allow_always").
        """
        self.events.on_permission = func
        return func

    def on_error(self, func: Callable[[Exception], Coroutine[Any, Any, None]]):
        """Register handler for errors."""
        self.events.on_error = func
        return func

    def on_complete(self, func: Callable[[], Coroutine[Any, Any, None]]):
        """Register handler for completion."""
        self.events.on_complete = func
        return func

    # --- Connection management ---

    async def connect(self) -> None:
        """Connect to the ACP agent."""
        if self._process is not None:
            return

        # Spawn the agent process
        self._process = await asyncio.create_subprocess_exec(
            self.command,
            *self.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self.cwd,
            env=self.env,
        )

        if self._process.stdin is None or self._process.stdout is None:
            raise RuntimeError("Failed to create subprocess pipes")

        # Create ACP connection
        # Note: ClientSideConnection expects (writer, reader) - stdin is writer, stdout is reader
        self._connection = ClientSideConnection(
            to_client=self._create_client_handler(),
            input_stream=self._process.stdin,
            output_stream=self._process.stdout,
        )

        # Initialize the connection
        init_response = await self._connection.initialize(
            protocol_version=1,
            client_info=Implementation(
                name="claude-code-acp-client",
                version="0.2.0",
            ),
        )
        logger.info(f"Connected to agent: {init_response.agent_info}")
        self._initialized = True

    async def disconnect(self) -> None:
        """Disconnect from the ACP agent."""
        if self._connection:
            await self._connection.close()
            self._connection = None

        if self._process:
            self._process.terminate()
            await self._process.wait()
            self._process = None

        self._initialized = False
        self._session_id = None

    async def __aenter__(self) -> "AcpClient":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.disconnect()

    # --- Session management ---

    async def new_session(self) -> str:
        """Create a new session."""
        if not self._connection:
            raise RuntimeError("Not connected")

        response = await self._connection.new_session(
            cwd=self.cwd,
            mcp_servers=[],
        )
        self._session_id = response.session_id
        return self._session_id

    async def prompt(self, text: str) -> str:
        """
        Send a prompt and receive the response.

        Events will be dispatched to registered handlers as they arrive.

        Args:
            text: The prompt text to send.

        Returns:
            The full text response.
        """
        if not self._connection:
            raise RuntimeError("Not connected")

        if not self._session_id:
            await self.new_session()

        self._text_buffer = ""

        try:
            response = await self._connection.prompt(
                prompt=[TextContentBlock(type="text", text=text)],
                session_id=self._session_id,
            )

            if self.events.on_complete:
                await self.events.on_complete()

            return self._text_buffer

        except Exception as e:
            if self.events.on_error:
                await self.events.on_error(e)
            raise

    async def cancel(self) -> None:
        """Cancel the current operation."""
        if self._connection and self._session_id:
            await self._connection.cancel(session_id=self._session_id)

    async def set_mode(self, mode: str) -> None:
        """Set the permission mode."""
        if not self._connection or not self._session_id:
            raise RuntimeError("No active session")

        await self._connection.set_session_mode(
            mode_id=mode,
            session_id=self._session_id,
        )

    # --- Internal handlers ---

    def _create_client_handler(self):
        """Create the client handler for receiving agent messages."""
        client = self

        class ClientHandler:
            """Handles incoming messages from the agent."""

            async def session_update(self, session_id: str, update: Any) -> None:
                """Handle session updates from the agent."""
                update_type = type(update).__name__

                if isinstance(update, AgentMessageChunk):
                    content = getattr(update, "content", None)
                    if content and hasattr(content, "text"):
                        text = content.text
                        if text and text not in client._text_buffer:
                            client._text_buffer += text
                            if client.events.on_text:
                                await client.events.on_text(text)

                elif isinstance(update, AgentThoughtChunk):
                    content = getattr(update, "content", None)
                    if content and hasattr(content, "text"):
                        if client.events.on_thinking:
                            await client.events.on_thinking(content.text)

                elif isinstance(update, ToolCallStart):
                    if client.events.on_tool_start:
                        await client.events.on_tool_start(
                            update.tool_call_id,
                            update.title or "",
                            update.raw_input or {},
                        )

                elif isinstance(update, ToolCallProgress):
                    if client.events.on_tool_end:
                        await client.events.on_tool_end(
                            update.tool_call_id,
                            update.status or "",
                            update.raw_output,
                        )

            async def request_permission(
                self,
                options: list[PermissionOption],
                session_id: str,
                tool_call: ToolCallUpdate,
                **kwargs: Any,
            ) -> RequestPermissionResponse:
                """Handle permission requests from the agent."""
                name = tool_call.title or "Unknown"
                raw_input = tool_call.raw_input or {}
                option_list = [{"id": o.option_id, "name": o.name} for o in options]

                # Default to allow
                selected_id = "allow"

                if client.events.on_permission:
                    selected_id = await client.events.on_permission(
                        name, raw_input, option_list
                    )

                return RequestPermissionResponse(
                    outcome={"outcome": "selected", "option_id": selected_id}
                )

            async def write_text_file(self, **kwargs) -> None:
                """Handle write file requests (stub)."""
                pass

            async def read_text_file(self, **kwargs) -> dict:
                """Handle read file requests (stub)."""
                return {"content": ""}

            async def create_terminal(self, **kwargs) -> dict:
                """Handle terminal creation (stub)."""
                return {"terminal_id": "stub"}

            async def terminal_output(self, **kwargs) -> dict:
                """Handle terminal output requests (stub)."""
                return {"output": ""}

            async def release_terminal(self, **kwargs) -> None:
                """Handle terminal release (stub)."""
                pass

            async def wait_for_terminal_exit(self, **kwargs) -> dict:
                """Handle terminal exit wait (stub)."""
                return {"exit_code": 0}

            async def kill_terminal(self, **kwargs) -> None:
                """Handle terminal kill (stub)."""
                pass

            async def ext_method(self, method: str, params: dict) -> dict:
                """Handle extension methods."""
                return {}

            async def ext_notification(self, method: str, params: dict) -> None:
                """Handle extension notifications."""
                pass

            def on_connect(self, conn: Any) -> None:
                """Called when connected."""
                pass

        return ClientHandler()
