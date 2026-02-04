"""
Claude ACP Agent - Bridges Claude Agent SDK with ACP protocol.

This module implements the ACP Agent interface, converting Claude SDK
messages to ACP session updates for bidirectional communication.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from acp import (
    Agent,
    InitializeResponse,
    NewSessionResponse,
    PromptResponse,
    SetSessionModeResponse,
    start_tool_call,
    text_block,
    update_agent_message,
    update_agent_thought,
    update_tool_call,
)
from acp.interfaces import Client
from acp.schema import (
    AgentCapabilities,
    AudioContentBlock,
    ClientCapabilities,
    EmbeddedResourceContentBlock,
    HttpMcpServer,
    ImageContentBlock,
    Implementation,
    McpServerStdio,
    PermissionOption,
    PromptCapabilities,
    ResourceContentBlock,
    SessionCapabilities,
    SseMcpServer,
    TextContentBlock,
)

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    Message,
    PermissionMode,
    PermissionResultAllow,
    PermissionResultDeny,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ThinkingBlock,
    ToolPermissionContext,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)
from claude_agent_sdk.types import StreamEvent

logger = logging.getLogger(__name__)


@dataclass
class Session:
    """Represents an active Claude session."""

    session_id: str
    cwd: str
    permission_mode: PermissionMode = "default"
    cancelled: bool = False
    tool_use_cache: dict[str, ToolUseBlock] = field(default_factory=dict)


class ClaudeAcpAgent(Agent):
    """
    ACP Agent implementation that bridges Claude Agent SDK with ACP protocol.

    This agent:
    1. Receives ACP requests from clients (Zed, Neovim, etc.)
    2. Converts them to Claude Agent SDK format
    3. Streams Claude responses back as ACP session updates
    4. Handles bidirectional communication (permissions, file ops, etc.)
    """

    def __init__(self) -> None:
        self._conn: Client | None = None
        self._sessions: dict[str, Session] = {}

    def on_connect(self, conn: Client) -> None:
        """Called when an ACP client connects."""
        self._conn = conn
        logger.info("ACP client connected")

    async def initialize(
        self,
        protocol_version: int,
        client_capabilities: ClientCapabilities | None = None,
        client_info: Implementation | None = None,
        **kwargs: Any,
    ) -> InitializeResponse:
        """Handle ACP initialize request."""
        logger.info(f"Initialize request from {client_info}")

        return InitializeResponse(
            protocol_version=protocol_version,
            agent_capabilities=AgentCapabilities(
                prompt_capabilities=PromptCapabilities(
                    image=True,
                    embedded_context=True,
                ),
                session_capabilities=SessionCapabilities(
                    fork={},
                    list={},
                    resume={},
                ),
            ),
            agent_info=Implementation(
                name="claude-code-acp-py",
                title="Claude Code (Python)",
                version="0.1.0",
            ),
            auth_methods=[
                {
                    "id": "claude-login",
                    "name": "Log in with Claude Code",
                    "description": "Run `claude /login` in the terminal",
                }
            ],
        )

    async def new_session(
        self,
        cwd: str,
        mcp_servers: list[HttpMcpServer | SseMcpServer | McpServerStdio],
        **kwargs: Any,
    ) -> NewSessionResponse:
        """Create a new Claude session."""
        session_id = str(uuid4())

        self._sessions[session_id] = Session(
            session_id=session_id,
            cwd=cwd,
        )

        logger.info(f"New session created: {session_id} in {cwd}")

        return NewSessionResponse(
            session_id=session_id,
            modes={
                "current_mode_id": "default",
                "available_modes": [
                    {
                        "id": "default",
                        "name": "Default",
                        "description": "Standard behavior, prompts for dangerous operations",
                    },
                    {
                        "id": "acceptEdits",
                        "name": "Accept Edits",
                        "description": "Auto-accept file edit operations",
                    },
                    {
                        "id": "plan",
                        "name": "Plan Mode",
                        "description": "Planning mode, no actual tool execution",
                    },
                    {
                        "id": "bypassPermissions",
                        "name": "Bypass Permissions",
                        "description": "Bypass all permission checks",
                    },
                ],
            },
        )

    async def set_session_mode(
        self, mode_id: str, session_id: str, **kwargs: Any
    ) -> SetSessionModeResponse | None:
        """Change the permission mode for a session."""
        if session_id not in self._sessions:
            raise ValueError(f"Session not found: {session_id}")

        valid_modes = ["default", "acceptEdits", "plan", "bypassPermissions", "dontAsk"]
        if mode_id not in valid_modes:
            raise ValueError(f"Invalid mode: {mode_id}")

        self._sessions[session_id].permission_mode = mode_id  # type: ignore
        logger.info(f"Session {session_id} mode changed to {mode_id}")

        return SetSessionModeResponse()

    async def prompt(
        self,
        prompt: list[
            TextContentBlock
            | ImageContentBlock
            | AudioContentBlock
            | ResourceContentBlock
            | EmbeddedResourceContentBlock
        ],
        session_id: str,
        **kwargs: Any,
    ) -> PromptResponse:
        """
        Handle a prompt from the ACP client.

        This is the main method that:
        1. Converts ACP prompt to Claude format
        2. Streams Claude responses via ClaudeSDKClient
        3. Converts Claude messages to ACP updates
        """
        if session_id not in self._sessions:
            raise ValueError(f"Session not found: {session_id}")

        session = self._sessions[session_id]
        session.cancelled = False

        # Convert ACP prompt to text
        prompt_text = self._convert_prompt_to_text(prompt)

        logger.info(f"Prompt for session {session_id}: {prompt_text[:100]}...")

        # Build Claude options with permission callback for bidirectional communication
        options = ClaudeAgentOptions(
            cwd=session.cwd,
            permission_mode=session.permission_mode,
            include_partial_messages=True,
        )

        # Add permission callback if not bypassing permissions
        if session.permission_mode != "bypassPermissions":
            options = ClaudeAgentOptions(
                cwd=session.cwd,
                permission_mode=session.permission_mode,
                include_partial_messages=True,
                can_use_tool=self._create_permission_handler(session_id),
            )

        try:
            # Use ClaudeSDKClient for streaming mode (required for can_use_tool callback)
            async with ClaudeSDKClient(options) as client:
                # Send the query
                await client.query(prompt_text)

                # Receive and process messages
                async for message in client.receive_response():
                    if session.cancelled:
                        await client.interrupt()
                        return PromptResponse(stop_reason="cancelled")

                    await self._handle_message(session_id, message)

        except Exception as e:
            logger.error(f"Error in prompt: {e}")
            raise

        return PromptResponse(stop_reason="end_turn")

    async def cancel(self, session_id: str, **kwargs: Any) -> None:
        """Cancel the current operation for a session."""
        if session_id in self._sessions:
            self._sessions[session_id].cancelled = True
            logger.info(f"Session {session_id} cancelled")

    # --- Conversion Methods ---

    def _convert_prompt_to_text(
        self,
        prompt: list[
            TextContentBlock
            | ImageContentBlock
            | AudioContentBlock
            | ResourceContentBlock
            | EmbeddedResourceContentBlock
        ],
    ) -> str:
        """Convert ACP prompt blocks to text for Claude."""
        parts = []

        for block in prompt:
            if isinstance(block, dict):
                block_type = block.get("type")
                if block_type == "text":
                    parts.append(block.get("text", ""))
                elif block_type == "resource":
                    resource = block.get("resource", {})
                    if "text" in resource:
                        uri = resource.get("uri", "unknown")
                        parts.append(f"\n<context ref=\"{uri}\">\n{resource['text']}\n</context>")
                elif block_type == "resource_link":
                    uri = block.get("uri", "")
                    name = block.get("name", uri.split("/")[-1])
                    parts.append(f"[@{name}]({uri})")
            elif hasattr(block, "text"):
                parts.append(block.text)

        return "\n".join(parts)

    async def _handle_message(self, session_id: str, message: Message) -> None:
        """Convert and emit a Claude message as ACP updates."""
        if self._conn is None:
            return

        session = self._sessions.get(session_id)
        if session is None:
            return

        if isinstance(message, AssistantMessage):
            await self._handle_assistant_message(session_id, message, session)

        elif isinstance(message, StreamEvent):
            await self._handle_stream_event(session_id, message)

        elif isinstance(message, SystemMessage):
            # System messages (init, status, etc.) - log but don't emit
            logger.debug(f"System message: {message.subtype}")

        elif isinstance(message, ResultMessage):
            # Result message - session complete
            logger.info(f"Session {session_id} completed: {message.subtype}")

        elif isinstance(message, UserMessage):
            # User messages from history - usually skip
            pass

    async def _handle_assistant_message(
        self, session_id: str, message: AssistantMessage, session: Session
    ) -> None:
        """Handle an assistant message from Claude."""
        if self._conn is None:
            return

        for block in message.content:
            if isinstance(block, TextBlock):
                # Text content
                await self._conn.session_update(
                    session_id,
                    update_agent_message(text_block(block.text)),
                )

            elif isinstance(block, ThinkingBlock):
                # Thinking/reasoning content
                await self._conn.session_update(
                    session_id,
                    update_agent_thought(text_block(block.thinking)),
                )

            elif isinstance(block, ToolUseBlock):
                # Tool invocation
                session.tool_use_cache[block.id] = block

                await self._conn.session_update(
                    session_id,
                    start_tool_call(
                        tool_call_id=block.id,
                        title=self._get_tool_title(block.name, block.input),
                        status="pending",
                        raw_input=block.input,
                    ),
                )

            elif isinstance(block, ToolResultBlock):
                # Tool result
                status = "failed" if block.is_error else "completed"

                await self._conn.session_update(
                    session_id,
                    update_tool_call(
                        tool_call_id=block.tool_use_id,
                        status=status,
                        raw_output=block.content,
                    ),
                )

    async def _handle_stream_event(self, session_id: str, event: StreamEvent) -> None:
        """Handle a streaming event from Claude."""
        if self._conn is None:
            return

        event_data = event.event
        event_type = event_data.get("type")

        if event_type == "content_block_delta":
            delta = event_data.get("delta", {})
            delta_type = delta.get("type")

            if delta_type == "text_delta":
                text = delta.get("text", "")
                if text:
                    await self._conn.session_update(
                        session_id,
                        update_agent_message(text_block(text)),
                    )

            elif delta_type == "thinking_delta":
                thinking = delta.get("thinking", "")
                if thinking:
                    await self._conn.session_update(
                        session_id,
                        update_agent_thought(text_block(thinking)),
                    )

    def _get_tool_title(self, tool_name: str, tool_input: dict[str, Any]) -> str:
        """Generate a human-readable title for a tool call."""
        if tool_name == "Read":
            path = tool_input.get("file_path", tool_input.get("path", ""))
            return f"Read {path}"
        elif tool_name in ["Write", "Edit"]:
            path = tool_input.get("file_path", tool_input.get("path", ""))
            return f"{tool_name} {path}"
        elif tool_name == "Bash":
            cmd = tool_input.get("command", "")
            return f"Run: {cmd[:50]}..." if len(cmd) > 50 else f"Run: {cmd}"
        elif tool_name == "Glob":
            pattern = tool_input.get("pattern", "")
            return f"Find files: {pattern}"
        elif tool_name == "Grep":
            pattern = tool_input.get("pattern", "")
            return f"Search: {pattern}"
        else:
            return tool_name

    def _create_permission_handler(self, session_id: str):
        """Create a permission handler for bidirectional permission requests."""

        async def can_use_tool(
            tool_name: str,
            tool_input: dict[str, Any],
            context: ToolPermissionContext,
        ) -> PermissionResultAllow | PermissionResultDeny:
            logger.info(f"🔧 Permission requested for tool: {tool_name}")

            if self._conn is None:
                logger.warning("No ACP connection for permission request")
                return PermissionResultDeny(message="No ACP connection")

            session = self._sessions.get(session_id)
            if session is None:
                return PermissionResultDeny(message="Session not found")

            # For certain modes, auto-allow
            if session.permission_mode == "bypassPermissions":
                return PermissionResultAllow()

            if session.permission_mode == "acceptEdits" and tool_name in [
                "Write",
                "Edit",
                "MultiEdit",
            ]:
                return PermissionResultAllow()

            # Request permission from ACP client
            tool_use_id = str(uuid4())

            response = await self._conn.request_permission(
                options=[
                    PermissionOption(
                        kind="allow_always",
                        name="Always Allow",
                        option_id="allow_always",
                    ),
                    PermissionOption(
                        kind="allow_once",
                        name="Allow",
                        option_id="allow",
                    ),
                    PermissionOption(
                        kind="reject_once",
                        name="Reject",
                        option_id="reject",
                    ),
                ],
                session_id=session_id,
                tool_call={
                    "tool_call_id": tool_use_id,
                    "title": self._get_tool_title(tool_name, tool_input),
                    "raw_input": tool_input,
                },
            )

            outcome = response.get("outcome", {})
            if outcome.get("outcome") == "selected":
                option_id = outcome.get("option_id")
                if option_id in ["allow", "allow_always"]:
                    return PermissionResultAllow()

            return PermissionResultDeny(message="User denied permission")

        return can_use_tool

    # --- Additional ACP Methods ---

    async def list_sessions(
        self,
        cursor: str | None = None,
        cwd: str | None = None,
        **kwargs: Any,
    ):
        """List available sessions."""
        from acp.schema import ListSessionsResponse, SessionInfo

        sessions = []
        for session_id, session in self._sessions.items():
            if cwd is None or session.cwd == cwd:
                sessions.append(
                    SessionInfo(
                        sessionId=session_id,
                        cwd=session.cwd,
                    )
                )

        return ListSessionsResponse(sessions=sessions)

    async def load_session(
        self,
        cwd: str,
        mcp_servers: list,
        session_id: str,
        **kwargs: Any,
    ):
        """Load an existing session."""
        from acp.schema import LoadSessionResponse

        if session_id not in self._sessions:
            return None

        session = self._sessions[session_id]
        session.cwd = cwd

        return LoadSessionResponse()

    async def fork_session(
        self,
        cwd: str,
        session_id: str,
        mcp_servers: list | None = None,
        **kwargs: Any,
    ):
        """Fork an existing session."""
        from acp.schema import ForkSessionResponse

        if session_id not in self._sessions:
            raise ValueError(f"Session not found: {session_id}")

        new_session_id = str(uuid4())
        old_session = self._sessions[session_id]

        self._sessions[new_session_id] = Session(
            session_id=new_session_id,
            cwd=cwd,
            permission_mode=old_session.permission_mode,
        )

        logger.info(f"Forked session {session_id} to {new_session_id}")

        return ForkSessionResponse(session_id=new_session_id)

    async def resume_session(
        self,
        cwd: str,
        session_id: str,
        mcp_servers: list | None = None,
        **kwargs: Any,
    ):
        """Resume an existing session."""
        from acp.schema import ResumeSessionResponse

        if session_id not in self._sessions:
            raise ValueError(f"Session not found: {session_id}")

        session = self._sessions[session_id]
        session.cwd = cwd
        session.cancelled = False

        logger.info(f"Resumed session {session_id}")

        return ResumeSessionResponse()

    async def authenticate(self, method_id: str, **kwargs: Any):
        """Handle authentication requests."""
        from acp.schema import AuthenticateResponse

        logger.info(f"Authentication requested: {method_id}")

        # For Claude login, the user needs to run `claude /login` in terminal
        # The AuthenticateResponse is empty per ACP spec - auth status is handled differently
        return AuthenticateResponse()

    async def set_session_model(
        self,
        model_id: str,
        session_id: str,
        **kwargs: Any,
    ):
        """Set the model for a session (stub - Claude CLI handles model selection)."""
        from acp.schema import SetSessionModelResponse

        logger.info(f"Model change requested for session {session_id}: {model_id}")
        # Note: Claude CLI handles model selection, this is just for compatibility
        return SetSessionModelResponse()

    # --- Extension Methods ---

    async def ext_method(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """Handle extension method calls."""
        logger.info(f"Extension method: {method}")
        return {"status": "ok"}

    async def ext_notification(self, method: str, params: dict[str, Any]) -> None:
        """Handle extension notifications."""
        logger.info(f"Extension notification: {method}")
