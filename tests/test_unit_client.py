"""Unit tests for ClaudeClient."""

import pytest

from claude_code_acp.client import ClaudeClient, ClaudeEvents


class TestClaudeEvents:
    """Tests for ClaudeEvents dataclass."""

    def test_events_default_none(self):
        """Test that all event handlers default to None."""
        events = ClaudeEvents()

        assert events.on_text is None
        assert events.on_thinking is None
        assert events.on_tool_start is None
        assert events.on_tool_end is None
        assert events.on_permission is None
        assert events.on_error is None
        assert events.on_complete is None


class TestClaudeClient:
    """Tests for ClaudeClient."""

    def test_client_initialization_default(self):
        """Test client initialization with defaults."""
        client = ClaudeClient()

        assert client.cwd == "."
        assert client.mcp_servers == []
        assert client.system_prompt is None
        assert client.session_id is None
        assert client.events is not None

    def test_client_initialization_custom(self):
        """Test client initialization with custom values."""
        mcp_servers = [{"name": "test", "command": "echo"}]
        client = ClaudeClient(
            cwd="/tmp",
            mcp_servers=mcp_servers,
            system_prompt="Custom prompt",
        )

        assert client.cwd == "/tmp"
        assert client.mcp_servers == mcp_servers
        assert client.system_prompt == "Custom prompt"

    def test_on_text_decorator(self):
        """Test on_text decorator registration."""
        client = ClaudeClient()

        @client.on_text
        async def handler(text: str):
            pass

        assert client.events.on_text is handler

    def test_on_thinking_decorator(self):
        """Test on_thinking decorator registration."""
        client = ClaudeClient()

        @client.on_thinking
        async def handler(text: str):
            pass

        assert client.events.on_thinking is handler

    def test_on_tool_start_decorator(self):
        """Test on_tool_start decorator registration."""
        client = ClaudeClient()

        @client.on_tool_start
        async def handler(tool_id: str, name: str, input: dict):
            pass

        assert client.events.on_tool_start is handler

    def test_on_tool_end_decorator(self):
        """Test on_tool_end decorator registration."""
        client = ClaudeClient()

        @client.on_tool_end
        async def handler(tool_id: str, status: str, output):
            pass

        assert client.events.on_tool_end is handler

    def test_on_permission_decorator(self):
        """Test on_permission decorator registration."""
        client = ClaudeClient()

        @client.on_permission
        async def handler(name: str, input: dict) -> bool:
            return True

        assert client.events.on_permission is handler

    def test_on_error_decorator(self):
        """Test on_error decorator registration."""
        client = ClaudeClient()

        @client.on_error
        async def handler(e: Exception):
            pass

        assert client.events.on_error is handler

    def test_on_complete_decorator(self):
        """Test on_complete decorator registration."""
        client = ClaudeClient()

        @client.on_complete
        async def handler():
            pass

        assert client.events.on_complete is handler

    def test_multiple_decorators(self):
        """Test registering multiple event handlers."""
        client = ClaudeClient()

        @client.on_text
        async def text_handler(text: str):
            pass

        @client.on_complete
        async def complete_handler():
            pass

        assert client.events.on_text is text_handler
        assert client.events.on_complete is complete_handler

    def test_decorator_returns_function(self):
        """Test that decorators return the original function."""
        client = ClaudeClient()

        @client.on_text
        async def my_handler(text: str):
            return text

        # The decorator should return the original function
        assert my_handler.__name__ == "my_handler"
