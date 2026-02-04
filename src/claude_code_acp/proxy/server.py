"""
ACP Proxy Server.

JSON-RPC server that implements the Copilot SDK protocol
and forwards requests to backend ACP servers.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import time
import uuid
from typing import Any

from .protocol import (
    SessionEventType,
    create_session_event,
    create_assistant_message_event,
)
from .session_manager import ProxySessionManager

logger = logging.getLogger(__name__)

# Protocol version that we claim to support
# SDK version 0.1.x expects protocol version 2
PROTOCOL_VERSION = 2
PROXY_VERSION = "0.1.0"


class AcpProxyServer:
    """
    JSON-RPC Server that bridges Copilot SDK to ACP backends.

    This server:
    1. Accepts connections from Copilot SDK
    2. Implements the Copilot SDK protocol
    3. Translates requests to standard ACP protocol
    4. Forwards to backend ACP servers (Gemini, Claude, etc.)
    """

    def __init__(
        self,
        backend: str = "gemini",
        backend_args: list[str] | None = None,
        cwd: str = ".",
        input_stream: asyncio.StreamReader | None = None,
        output_stream: asyncio.StreamWriter | None = None,
    ):
        """
        Initialize the proxy server.

        Args:
            backend: Backend CLI to use ("gemini", "claude-code-acp", "copilot").
            backend_args: Additional arguments for the backend.
            cwd: Default working directory.
            input_stream: Input stream (defaults to stdin).
            output_stream: Output stream (defaults to stdout).
        """
        self.backend = backend
        self.backend_args = backend_args or []
        self.cwd = cwd

        self._input_stream = input_stream
        self._output_stream = output_stream
        self._session_manager: ProxySessionManager | None = None
        self._running = False
        self._request_id_counter = 0
        self._pending_requests: dict[str | int, asyncio.Future] = {}

    async def start(self) -> None:
        """Start the proxy server."""
        # Initialize session manager
        self._session_manager = ProxySessionManager(
            backend_command=self.backend,
            backend_args=self.backend_args,
            default_cwd=self.cwd,
        )

        # Set up stdio if not provided
        if self._input_stream is None:
            # Create reader from stdin
            loop = asyncio.get_event_loop()
            self._input_stream = asyncio.StreamReader()
            protocol = asyncio.StreamReaderProtocol(self._input_stream)
            await loop.connect_read_pipe(lambda: protocol, sys.stdin)

        if self._output_stream is None:
            # Create writer to stdout
            loop = asyncio.get_event_loop()
            transport, protocol = await loop.connect_write_pipe(
                asyncio.streams.FlowControlMixin, sys.stdout
            )
            self._output_stream = asyncio.StreamWriter(
                transport, protocol, None, loop
            )

        self._running = True
        logger.info(f"ACP Proxy Server started (backend: {self.backend})")

        # Start message processing loop
        await self._process_messages()

    async def stop(self) -> None:
        """Stop the proxy server."""
        self._running = False

        if self._session_manager:
            await self._session_manager.close_all()

        logger.info("ACP Proxy Server stopped")

    async def _process_messages(self) -> None:
        """Process incoming JSON-RPC messages with LSP-style Content-Length framing."""
        while self._running:
            try:
                # Read Content-Length header
                header_line = await self._input_stream.readline()
                if not header_line:
                    # EOF
                    break

                header = header_line.decode("utf-8").strip()
                if not header:
                    continue

                # Parse Content-Length
                if not header.startswith("Content-Length:"):
                    logger.warning(f"Expected Content-Length header, got: {header}")
                    continue

                try:
                    content_length = int(header.split(":")[1].strip())
                except (IndexError, ValueError) as e:
                    logger.error(f"Invalid Content-Length: {header}")
                    continue

                # Read empty line (CRLF separator)
                await self._input_stream.readline()

                # Read exact content
                content_bytes = await self._read_exact(content_length)
                content = content_bytes.decode("utf-8")

                # Parse JSON-RPC message
                try:
                    message = json.loads(content)
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON: {e}")
                    await self._send_error(None, -32700, "Parse error")
                    continue

                # Handle the message
                await self._handle_message(message)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Error processing message: {e}")

    async def _read_exact(self, num_bytes: int) -> bytes:
        """Read exactly num_bytes from the input stream."""
        chunks = []
        remaining = num_bytes
        while remaining > 0:
            chunk = await self._input_stream.read(remaining)
            if not chunk:
                raise EOFError("Unexpected end of stream")
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)

    async def _handle_message(self, message: dict) -> None:
        """Handle a JSON-RPC message."""
        # Check if it's a request or notification
        msg_id = message.get("id")
        method = message.get("method", "")
        params = message.get("params", {})

        logger.debug(f"Received: {method} (id={msg_id})")

        # Route to appropriate handler
        handler = self._get_handler(method)
        if not handler:
            if msg_id is not None:
                await self._send_error(msg_id, -32601, f"Method not found: {method}")
            return

        try:
            result = await handler(params)
            if msg_id is not None:
                await self._send_result(msg_id, result)
        except Exception as e:
            logger.exception(f"Error handling {method}: {e}")
            if msg_id is not None:
                await self._send_error(msg_id, -32603, str(e))

    def _get_handler(self, method: str):
        """Get the handler for a method."""
        handlers = {
            "ping": self._handle_ping,
            "status.get": self._handle_status_get,
            "auth.getStatus": self._handle_auth_get_status,
            "models.list": self._handle_models_list,
            "session.create": self._handle_session_create,
            "session.resume": self._handle_session_resume,
            "session.send": self._handle_session_send,
            "session.destroy": self._handle_session_destroy,
            "session.abort": self._handle_session_abort,
            "session.list": self._handle_session_list,
            "session.delete": self._handle_session_delete,
            "session.getMessages": self._handle_session_get_messages,
            "session.getLastId": self._handle_session_get_last_id,
            "session.getForeground": self._handle_session_get_foreground,
            "session.setForeground": self._handle_session_set_foreground,
        }
        return handlers.get(method)

    # ========================================================================
    # Message Sending
    # ========================================================================

    async def _send_result(self, msg_id: str | int, result: Any) -> None:
        """Send a successful response."""
        response = {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": result,
        }
        await self._send_message(response)

    async def _send_error(
        self,
        msg_id: str | int | None,
        code: int,
        message: str,
        data: Any = None,
    ) -> None:
        """Send an error response."""
        response = {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {
                "code": code,
                "message": message,
            },
        }
        if data is not None:
            response["error"]["data"] = data
        await self._send_message(response)

    async def _send_notification(self, method: str, params: dict) -> None:
        """Send a notification (no id, no response expected)."""
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
        }
        await self._send_message(notification)

    async def _send_session_event(self, session_id: str, event: dict) -> None:
        """Send a session event notification."""
        await self._send_notification("session.event", {
            "sessionId": session_id,
            "event": event,
        })

    async def _send_message(self, message: dict) -> None:
        """Send a JSON-RPC message with LSP-style Content-Length framing."""
        content = json.dumps(message, separators=(",", ":"))
        content_bytes = content.encode("utf-8")
        header = f"Content-Length: {len(content_bytes)}\r\n\r\n"

        self._output_stream.write(header.encode("utf-8"))
        self._output_stream.write(content_bytes)
        await self._output_stream.drain()
        logger.debug(f"Sent: {message.get('method', message.get('id', 'response'))}")

    # ========================================================================
    # Method Handlers
    # ========================================================================

    async def _handle_ping(self, params: dict) -> dict:
        """Handle ping request."""
        # message field is required by SDK
        message = params.get("message") if params.get("message") else "pong"
        return {
            "message": message,
            "timestamp": int(time.time() * 1000),
            "protocolVersion": PROTOCOL_VERSION,
        }

    async def _handle_status_get(self, params: dict) -> dict:
        """Handle status.get request."""
        return {
            "version": PROXY_VERSION,
            "protocolVersion": PROTOCOL_VERSION,
        }

    async def _handle_auth_get_status(self, params: dict) -> dict:
        """Handle auth.getStatus request."""
        # We always report as authenticated (via env/proxy)
        return {
            "isAuthenticated": True,
            "authType": "env",
            "host": "https://github.com",
            "login": "proxy-user",
            "statusMessage": f"Connected via ACP Proxy to {self.backend}",
        }

    async def _handle_models_list(self, params: dict) -> dict:
        """Handle models.list request."""
        # Return models based on backend
        models = []

        if self.backend == "gemini":
            models = [
                {
                    "id": "gemini-2.0-flash",
                    "name": "Gemini 2.0 Flash",
                    "capabilities": {"supports": {"vision": True}},
                },
                {
                    "id": "gemini-1.5-pro",
                    "name": "Gemini 1.5 Pro",
                    "capabilities": {"supports": {"vision": True}},
                },
            ]
        elif self.backend in ("claude-code", "claude-code-acp"):
            models = [
                {
                    "id": "claude-sonnet-4-20250514",
                    "name": "Claude Sonnet 4",
                    "capabilities": {"supports": {"vision": True, "reasoningEffort": True}},
                },
                {
                    "id": "claude-opus-4-20250514",
                    "name": "Claude Opus 4",
                    "capabilities": {"supports": {"vision": True, "reasoningEffort": True}},
                },
            ]
        else:
            # Generic model
            models = [
                {
                    "id": "default",
                    "name": "Default Model",
                    "capabilities": {},
                }
            ]

        return {"models": models}

    async def _handle_session_create(self, params: dict) -> dict:
        """Handle session.create request."""
        session_id = params.get("sessionId")
        model = params.get("model")
        cwd = params.get("workingDirectory", self.cwd)
        mcp_servers = params.get("mcpServers")

        # Create event callback
        async def event_callback(event: dict):
            await self._send_session_event(session.session_id, event)

        # Create session
        session = await self._session_manager.create_session(
            session_id=session_id,
            model=model,
            working_directory=cwd,
            mcp_servers=mcp_servers,
            event_callback=event_callback,
        )

        # Send session.start event
        start_event = create_session_event(
            SessionEventType.SESSION_START,
            {"cwd": cwd, "model": model or "default"}
        )
        await self._send_session_event(session.session_id, start_event)

        return {
            "sessionId": session.session_id,
            "workspacePath": cwd,
        }

    async def _handle_session_resume(self, params: dict) -> dict:
        """Handle session.resume request."""
        session_id = params.get("sessionId")
        if not session_id:
            raise ValueError("sessionId is required")

        # Check if session exists
        session = self._session_manager.get_session(session_id)

        if session:
            # Session exists, reuse it
            # Update event callback
            async def event_callback(event: dict):
                await self._send_session_event(session.session_id, event)
            session.event_callback = event_callback

            # Send session.resume event
            resume_event = create_session_event(
                SessionEventType.SESSION_RESUME,
                {"cwd": session.working_directory}
            )
            await self._send_session_event(session.session_id, resume_event)

            return {
                "sessionId": session.session_id,
                "workspacePath": session.working_directory,
            }
        else:
            # Session doesn't exist, create new one with the given ID
            return await self._handle_session_create(params)

    async def _handle_session_send(self, params: dict) -> dict:
        """Handle session.send request."""
        session_id = params.get("sessionId")
        prompt = params.get("prompt", "")
        attachments = params.get("attachments")

        if not session_id:
            raise ValueError("sessionId is required")
        if not prompt:
            raise ValueError("prompt is required")

        # Generate message ID
        message_id = str(uuid.uuid4())

        # Send user message event
        user_event = create_session_event(
            SessionEventType.USER_MESSAGE,
            {"content": prompt, "messageId": message_id}
        )
        await self._send_session_event(session_id, user_event)

        # Send turn start event
        turn_id = str(uuid.uuid4())
        turn_start_event = create_session_event(
            SessionEventType.ASSISTANT_TURN_START,
            {"turnId": turn_id}
        )
        await self._send_session_event(session_id, turn_start_event)

        # Send message to backend (this will trigger events via callbacks)
        try:
            response = await self._session_manager.send_message(
                session_id, prompt, attachments
            )

            # Send final assistant message event
            final_event = create_assistant_message_event(response, str(uuid.uuid4()))
            await self._send_session_event(session_id, final_event)

        except Exception as e:
            # Send error event
            error_event = create_session_event(
                SessionEventType.SESSION_ERROR,
                {"error": str(e)}
            )
            await self._send_session_event(session_id, error_event)
            raise

        return {"messageId": message_id}

    async def _handle_session_destroy(self, params: dict) -> dict:
        """Handle session.destroy request."""
        session_id = params.get("sessionId")
        if session_id:
            # Send shutdown event
            shutdown_event = create_session_event(SessionEventType.SESSION_SHUTDOWN, {})
            await self._send_session_event(session_id, shutdown_event)

            await self._session_manager.destroy_session(session_id)
        return {}

    async def _handle_session_abort(self, params: dict) -> dict:
        """Handle session.abort request."""
        session_id = params.get("sessionId")
        if session_id:
            await self._session_manager.abort_session(session_id)

            # Send abort event
            abort_event = create_session_event(SessionEventType.ABORT, {})
            await self._send_session_event(session_id, abort_event)
        return {}

    async def _handle_session_list(self, params: dict) -> dict:
        """Handle session.list request."""
        sessions = self._session_manager.list_sessions()
        return {"sessions": sessions}

    async def _handle_session_delete(self, params: dict) -> dict:
        """Handle session.delete request."""
        session_id = params.get("sessionId")
        success = False
        if session_id:
            success = await self._session_manager.delete_session(session_id)
        return {"success": success}

    async def _handle_session_get_messages(self, params: dict) -> dict:
        """Handle session.getMessages request."""
        session_id = params.get("sessionId")
        events = []
        if session_id:
            events = self._session_manager.get_session_events(session_id)
        return {"events": events}

    async def _handle_session_get_last_id(self, params: dict) -> dict:
        """Handle session.getLastId request."""
        session_id = self._session_manager.get_last_session_id()
        return {"sessionId": session_id}

    async def _handle_session_get_foreground(self, params: dict) -> dict:
        """Handle session.getForeground request (TUI mode - not applicable)."""
        return {"sessionId": self._session_manager.get_last_session_id()}

    async def _handle_session_set_foreground(self, params: dict) -> dict:
        """Handle session.setForeground request (TUI mode - not applicable)."""
        return {"success": True}


async def run_proxy_server(
    backend: str = "gemini",
    backend_args: list[str] | None = None,
    cwd: str = ".",
) -> None:
    """
    Run the ACP Proxy Server.

    Args:
        backend: Backend CLI to use.
        backend_args: Additional arguments for the backend.
        cwd: Default working directory.
    """
    server = AcpProxyServer(
        backend=backend,
        backend_args=backend_args,
        cwd=cwd,
    )

    try:
        await server.start()
    except KeyboardInterrupt:
        pass
    finally:
        await server.stop()
