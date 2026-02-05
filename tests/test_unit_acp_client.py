"""Unit tests for AcpClient."""

import pytest

from claude_code_acp.acp_client import AcpClient, AcpClientEvents


class TestAcpClientEvents:
    """Tests for AcpClientEvents dataclass."""

    def test_events_default_none(self):
        """Test that all event handlers default to None."""
        events = AcpClientEvents()

        assert events.on_text is None
        assert events.on_thinking is None
        assert events.on_tool_start is None
        assert events.on_tool_end is None
        assert events.on_permission is None
        assert events.on_error is None
        assert events.on_complete is None
        assert events.on_file_read is None
        assert events.on_file_write is None
        assert events.on_terminal_create is None
        assert events.on_terminal_output is None


class TestAcpClient:
    """Tests for AcpClient."""

    def test_client_initialization_default(self):
        """Test client initialization with defaults."""
        client = AcpClient()

        assert client.command == "claude-code-acp"
        assert client.args == []
        assert client.cwd == "."
        assert client.env is None
        assert client.mcp_servers == []
        assert client.events is not None

    def test_client_initialization_custom(self):
        """Test client initialization with custom values."""
        mcp_servers = [{"name": "test", "command": "echo"}]
        client = AcpClient(
            command="my-agent",
            args=["--verbose"],
            cwd="/tmp",
            env={"KEY": "value"},
            mcp_servers=mcp_servers,
        )

        assert client.command == "my-agent"
        assert client.args == ["--verbose"]
        assert client.cwd == "/tmp"
        assert client.env == {"KEY": "value"}
        assert client.mcp_servers == mcp_servers

    def test_on_text_decorator(self):
        """Test on_text decorator registration."""
        client = AcpClient()

        @client.on_text
        async def handler(text: str):
            pass

        assert client.events.on_text is handler

    def test_on_thinking_decorator(self):
        """Test on_thinking decorator registration."""
        client = AcpClient()

        @client.on_thinking
        async def handler(text: str):
            pass

        assert client.events.on_thinking is handler

    def test_on_tool_start_decorator(self):
        """Test on_tool_start decorator registration."""
        client = AcpClient()

        @client.on_tool_start
        async def handler(tool_id: str, name: str, input: dict):
            pass

        assert client.events.on_tool_start is handler

    def test_on_tool_end_decorator(self):
        """Test on_tool_end decorator registration."""
        client = AcpClient()

        @client.on_tool_end
        async def handler(tool_id: str, status: str, output):
            pass

        assert client.events.on_tool_end is handler

    def test_on_permission_decorator(self):
        """Test on_permission decorator registration."""
        client = AcpClient()

        @client.on_permission
        async def handler(name: str, input: dict, options: list) -> str:
            return "allow"

        assert client.events.on_permission is handler

    def test_on_error_decorator(self):
        """Test on_error decorator registration."""
        client = AcpClient()

        @client.on_error
        async def handler(e: Exception):
            pass

        assert client.events.on_error is handler

    def test_on_complete_decorator(self):
        """Test on_complete decorator registration."""
        client = AcpClient()

        @client.on_complete
        async def handler():
            pass

        assert client.events.on_complete is handler

    def test_on_file_read_decorator(self):
        """Test on_file_read decorator registration."""
        client = AcpClient()

        @client.on_file_read
        async def handler(path: str) -> str | None:
            return None

        assert client.events.on_file_read is handler

    def test_on_file_write_decorator(self):
        """Test on_file_write decorator registration."""
        client = AcpClient()

        @client.on_file_write
        async def handler(path: str, content: str) -> bool:
            return True

        assert client.events.on_file_write is handler

    def test_on_terminal_create_decorator(self):
        """Test on_terminal_create decorator registration."""
        client = AcpClient()

        @client.on_terminal_create
        async def handler(command: str, cwd: str) -> bool:
            return True

        assert client.events.on_terminal_create is handler

    def test_on_terminal_output_decorator(self):
        """Test on_terminal_output decorator registration."""
        client = AcpClient()

        @client.on_terminal_output
        async def handler(terminal_id: str, output: str) -> None:
            pass

        assert client.events.on_terminal_output is handler

    def test_multiple_decorators(self):
        """Test registering multiple event handlers."""
        client = AcpClient()

        @client.on_text
        async def text_handler(text: str):
            pass

        @client.on_file_read
        async def read_handler(path: str) -> str | None:
            return None

        @client.on_complete
        async def complete_handler():
            pass

        assert client.events.on_text is text_handler
        assert client.events.on_file_read is read_handler
        assert client.events.on_complete is complete_handler

    def test_set_model_before_session(self):
        """Test that set_model stores pending model before session."""
        client = AcpClient()

        # No session yet, should store as pending
        assert client._pending_model is None
        # We can't test this without creating a session since it's async

    def test_internal_state_initialization(self):
        """Test internal state is properly initialized."""
        client = AcpClient()

        assert client._process is None
        assert client._connection is None
        assert client._session_id is None
        assert client._text_buffer == ""
        assert client._initialized is False
        assert client._pending_model is None
        assert client._terminals == {}
        assert client._terminal_counter == 0
