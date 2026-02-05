"""Integration tests for Claude connection.

These tests require:
- Claude CLI installed and authenticated
- Active Claude subscription

Run with: pytest tests/test_integration_connection.py -v
"""

import pytest

from claude_code_acp import AcpClient, ClaudeClient

from .conftest import requires_claude_cli, requires_claude_subscription


@pytest.mark.integration
@requires_claude_cli
@requires_claude_subscription
class TestClaudeClientConnection:
    """Integration tests for ClaudeClient."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_simple_query(self, temp_dir):
        """Test basic query-response with ClaudeClient."""
        client = ClaudeClient(cwd=str(temp_dir))

        received_text = []

        @client.on_text
        async def on_text(text: str):
            received_text.append(text)

        @client.on_permission
        async def on_permission(name: str, input: dict) -> bool:
            return True

        response = await client.query("Say 'Hello Test' and nothing else.")

        assert len(response) > 0
        assert "hello" in response.lower() or "test" in response.lower()
        assert len(received_text) > 0

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_session_creation(self, temp_dir):
        """Test session creation."""
        client = ClaudeClient(cwd=str(temp_dir))

        session_id = await client.start_session()

        assert session_id is not None
        assert client.session_id == session_id

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_event_handlers_called(self, temp_dir):
        """Test that event handlers are called properly."""
        client = ClaudeClient(cwd=str(temp_dir))

        events_received = {
            "text": False,
            "complete": False,
        }

        @client.on_text
        async def on_text(text: str):
            events_received["text"] = True

        @client.on_complete
        async def on_complete():
            events_received["complete"] = True

        @client.on_permission
        async def on_permission(name: str, input: dict) -> bool:
            return True

        await client.query("Hi")

        assert events_received["text"], "on_text was not called"
        assert events_received["complete"], "on_complete was not called"

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_set_mode(self, temp_dir):
        """Test setting permission mode."""
        client = ClaudeClient(cwd=str(temp_dir))

        # Start session and set mode
        await client.start_session()
        await client.set_mode("bypassPermissions")

        # Should be able to query without permission prompts
        response = await client.query("Say 'OK'")
        assert len(response) > 0


@pytest.mark.integration
@requires_claude_cli
@requires_claude_subscription
class TestAcpClientConnection:
    """Integration tests for AcpClient."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_connect_disconnect(self, temp_dir):
        """Test connecting and disconnecting from ACP agent."""
        client = AcpClient(
            command="claude-code-acp",
            cwd=str(temp_dir),
        )

        await client.connect()
        assert client._initialized is True
        assert client._process is not None

        await client.disconnect()
        assert client._initialized is False
        assert client._process is None

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_context_manager(self, temp_dir):
        """Test using AcpClient as context manager."""
        client = AcpClient(
            command="claude-code-acp",
            cwd=str(temp_dir),
        )

        async with client:
            assert client._initialized is True

        assert client._initialized is False

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_simple_prompt(self, temp_dir):
        """Test basic prompt with AcpClient."""
        client = AcpClient(
            command="claude-code-acp",
            cwd=str(temp_dir),
        )

        received_text = []

        @client.on_text
        async def on_text(text: str):
            received_text.append(text)

        @client.on_permission
        async def on_permission(name: str, input: dict, options: list) -> str:
            return "allow"

        async with client:
            response = await client.prompt("Say 'Hello ACP' and nothing else.")

        assert len(response) > 0
        assert "hello" in response.lower() or "acp" in response.lower()

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_new_session(self, temp_dir):
        """Test creating a new session."""
        client = AcpClient(
            command="claude-code-acp",
            cwd=str(temp_dir),
        )

        async with client:
            session_id = await client.new_session()
            # Check inside context manager (before disconnect clears it)
            assert session_id is not None
            assert client._session_id == session_id

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_event_handlers(self, temp_dir):
        """Test that event handlers are called."""
        client = AcpClient(
            command="claude-code-acp",
            cwd=str(temp_dir),
        )

        events = {
            "text": False,
            "complete": False,
        }

        @client.on_text
        async def on_text(text: str):
            events["text"] = True

        @client.on_complete
        async def on_complete():
            events["complete"] = True

        @client.on_permission
        async def on_permission(name: str, input: dict, options: list) -> str:
            return "allow"

        async with client:
            await client.prompt("Hi")

        assert events["text"], "on_text was not called"
        assert events["complete"], "on_complete was not called"

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_set_mode(self, temp_dir):
        """Test setting permission mode via ACP."""
        client = AcpClient(
            command="claude-code-acp",
            cwd=str(temp_dir),
        )

        async with client:
            await client.new_session()
            await client.set_mode("bypassPermissions")

            response = await client.prompt("Say 'Mode OK'")
            assert len(response) > 0

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_cancel(self, temp_dir):
        """Test cancelling a request."""
        client = AcpClient(
            command="claude-code-acp",
            cwd=str(temp_dir),
        )

        async with client:
            await client.new_session()
            # Cancel should not raise
            await client.cancel()
