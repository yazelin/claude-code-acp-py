"""
Session Manager for ACP Proxy.

Manages proxy sessions and their connections to backend ACP servers.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Coroutine

from ..acp_client import AcpClient

logger = logging.getLogger(__name__)


@dataclass
class ProxySession:
    """Represents a proxy session."""

    session_id: str
    backend_client: AcpClient | None = None
    model: str | None = None
    working_directory: str = "."
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)
    events: list[dict] = field(default_factory=list)
    is_active: bool = True

    # Callback for sending events to SDK
    event_callback: Callable[[dict], Coroutine[Any, Any, None]] | None = None


class ProxySessionManager:
    """
    Manages multiple proxy sessions.

    Each session connects to a backend ACP server and translates
    between Copilot SDK protocol and standard ACP protocol.
    """

    def __init__(
        self,
        backend_command: str = "gemini",
        backend_args: list[str] | None = None,
        default_cwd: str = ".",
    ):
        """
        Initialize the session manager.

        Args:
            backend_command: Command to run the backend ACP server.
            backend_args: Arguments for the backend command.
            default_cwd: Default working directory.
        """
        self.backend_command = backend_command
        self.backend_args = backend_args or []
        self.default_cwd = default_cwd

        self._sessions: dict[str, ProxySession] = {}
        self._last_session_id: str | None = None

    async def create_session(
        self,
        session_id: str | None = None,
        model: str | None = None,
        working_directory: str | None = None,
        mcp_servers: dict | None = None,
        event_callback: Callable[[dict], Coroutine[Any, Any, None]] | None = None,
        **kwargs,
    ) -> ProxySession:
        """
        Create a new proxy session.

        Args:
            session_id: Custom session ID (generated if not provided).
            model: Model to use (passed to backend if supported).
            working_directory: Working directory for the session.
            mcp_servers: MCP server configurations.
            event_callback: Callback for sending events to SDK.
            **kwargs: Additional session parameters.

        Returns:
            The created ProxySession.
        """
        # Generate session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())

        cwd = working_directory or self.default_cwd

        # Convert MCP servers from Copilot format to ACP format
        mcp_servers_acp = self._convert_mcp_servers(mcp_servers)

        # Determine backend args based on command
        backend_args = list(self.backend_args)
        if self.backend_command == "gemini":
            # Gemini uses --experimental-acp
            if "--experimental-acp" not in backend_args:
                backend_args.append("--experimental-acp")
            # Gemini: pass model as CLI argument (doesn't support set_session_model)
            if model and "--model" not in backend_args and "-m" not in backend_args:
                backend_args.extend(["--model", model])
        elif self.backend_command in ("claude", "claude-code", "claude-code-acp"):
            # Claude code already runs in ACP mode (no additional flags needed)
            # Model is set via set_session_model ACP method
            pass
        elif self.backend_command == "copilot":
            # Copilot uses --acp
            if "--acp" not in backend_args:
                backend_args.append("--acp")
            # Copilot: pass model as CLI argument (doesn't support set_session_model)
            if model and "--model" not in backend_args:
                backend_args.extend(["--model", model])

        # Create backend client
        backend_client = AcpClient(
            command=self.backend_command,
            args=backend_args,
            cwd=cwd,
            mcp_servers=mcp_servers_acp,
        )

        # Create session object
        session = ProxySession(
            session_id=session_id,
            backend_client=backend_client,
            model=model,
            working_directory=cwd,
            event_callback=event_callback,
        )

        # Register event handlers on backend client
        self._setup_backend_handlers(session)

        # Connect to backend
        try:
            await backend_client.connect()
            logger.info(f"Session {session_id} connected to backend: {self.backend_command}")

            # Set model if specified
            if model:
                try:
                    await backend_client.set_model(model)
                    logger.info(f"Set model for session {session_id}: {model}")
                except Exception as e:
                    logger.warning(f"Failed to set model (backend may not support it): {e}")
        except Exception as e:
            logger.error(f"Failed to connect to backend: {e}")
            raise

        # Store session
        self._sessions[session_id] = session
        self._last_session_id = session_id

        return session

    async def send_message(
        self,
        session_id: str,
        prompt: str,
        attachments: list[dict] | None = None,
    ) -> str:
        """
        Send a message to a session.

        Args:
            session_id: The session ID.
            prompt: The message to send.
            attachments: Optional attachments.

        Returns:
            The full response text.
        """
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        if not session.backend_client:
            raise RuntimeError(f"Session {session_id} has no backend client")

        # Update modified time
        session.modified_at = datetime.now()

        # Send to backend and get response
        response = await session.backend_client.prompt(prompt)

        return response

    async def destroy_session(self, session_id: str) -> None:
        """
        Destroy a session.

        Args:
            session_id: The session ID to destroy.
        """
        session = self._sessions.get(session_id)
        if not session:
            return

        session.is_active = False

        # Disconnect backend
        if session.backend_client:
            try:
                await session.backend_client.disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting backend: {e}")

        logger.info(f"Session {session_id} destroyed")

    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session permanently.

        Args:
            session_id: The session ID to delete.

        Returns:
            True if deleted, False if not found.
        """
        await self.destroy_session(session_id)

        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def get_session(self, session_id: str) -> ProxySession | None:
        """Get a session by ID."""
        return self._sessions.get(session_id)

    def list_sessions(self) -> list[dict]:
        """List all sessions."""
        return [
            {
                "sessionId": s.session_id,
                "startTime": s.created_at.isoformat(),
                "modifiedTime": s.modified_at.isoformat(),
                "summary": f"Session with {self.backend_command}",
                "isRemote": False,
            }
            for s in self._sessions.values()
        ]

    def get_last_session_id(self) -> str | None:
        """Get the last active session ID."""
        return self._last_session_id

    def get_session_events(self, session_id: str) -> list[dict]:
        """Get events for a session."""
        session = self._sessions.get(session_id)
        if not session:
            return []
        return session.events

    async def abort_session(self, session_id: str) -> None:
        """Abort the current operation in a session."""
        session = self._sessions.get(session_id)
        if session and session.backend_client:
            try:
                await session.backend_client.cancel()
            except Exception as e:
                logger.warning(f"Error aborting session: {e}")

    async def close_all(self) -> None:
        """Close all sessions."""
        for session_id in list(self._sessions.keys()):
            await self.destroy_session(session_id)
        self._sessions.clear()

    def _convert_mcp_servers(self, mcp_servers: dict | None) -> list[dict]:
        """
        Convert Copilot MCP server format to ACP format.

        Copilot format:
            {"name": {"type": "local", "command": "...", "args": [...], "tools": ["*"]}}

        ACP format:
            [{"name": "...", "command": "...", "args": [...], "env": {...}}]
        """
        if not mcp_servers:
            return []

        result = []
        for name, config in mcp_servers.items():
            server = {
                "name": name,
                "command": config.get("command", ""),
                "args": config.get("args", []),
            }

            # Handle environment variables
            if "env" in config:
                # Copilot uses ${VAR} syntax, we need to expand them
                env = {}
                for k, v in config["env"].items():
                    if isinstance(v, str) and v.startswith("${") and v.endswith("}"):
                        # Reference to environment variable
                        import os
                        var_name = v[2:-1]
                        env[k] = os.environ.get(var_name, "")
                    else:
                        env[k] = v
                server["env"] = env

            result.append(server)

        return result

    def _setup_backend_handlers(self, session: ProxySession) -> None:
        """Set up event handlers on the backend client."""
        if not session.backend_client:
            return

        from .protocol import (
            create_session_event,
            create_assistant_message_delta_event,
            create_tool_execution_start_event,
            create_tool_execution_complete_event,
            SessionEventType,
        )

        client = session.backend_client

        @client.on_text
        async def on_text(text: str):
            """Handle text from backend."""
            event = create_assistant_message_delta_event(text)
            session.events.append(event)
            if session.event_callback:
                await session.event_callback(event)

        @client.on_thinking
        async def on_thinking(text: str):
            """Handle thinking from backend."""
            event = create_session_event(
                SessionEventType.ASSISTANT_REASONING_DELTA,
                {"deltaContent": text}
            )
            session.events.append(event)
            if session.event_callback:
                await session.event_callback(event)

        @client.on_tool_start
        async def on_tool_start(tool_id: str, name: str, input_data: dict):
            """Handle tool start from backend."""
            event = create_tool_execution_start_event(tool_id, name, input_data)
            session.events.append(event)
            if session.event_callback:
                await session.event_callback(event)

        @client.on_tool_end
        async def on_tool_end(tool_id: str, status: str, output: Any):
            """Handle tool end from backend."""
            event = create_tool_execution_complete_event(
                tool_id,
                success=(status == "success" or status == ""),
                result=output
            )
            session.events.append(event)
            if session.event_callback:
                await session.event_callback(event)

        @client.on_permission
        async def on_permission(name: str, input_data: dict, options: list) -> str:
            """Handle permission request from backend."""
            # For now, auto-approve
            # TODO: Forward to SDK if requestPermission is True
            return "allow"

        @client.on_complete
        async def on_complete():
            """Handle completion from backend."""
            # Send turn end and idle events
            turn_end_event = create_session_event(
                SessionEventType.ASSISTANT_TURN_END,
                {"turnId": str(uuid.uuid4())}
            )
            idle_event = create_session_event(SessionEventType.SESSION_IDLE, {})

            session.events.extend([turn_end_event, idle_event])

            if session.event_callback:
                await session.event_callback(turn_end_event)
                await session.event_callback(idle_event)
