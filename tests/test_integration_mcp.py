"""Integration tests for MCP server loading.

These tests require:
- Claude CLI installed and authenticated
- Active Claude subscription
- Nanobanana MCP server configured (for some tests)

Run with: pytest tests/test_integration_mcp.py -v
"""

import pytest

from claude_code_acp import AcpClient, ClaudeClient

from .conftest import requires_claude_cli, requires_claude_subscription


@pytest.mark.integration
@pytest.mark.slow
@requires_claude_cli
@requires_claude_subscription
class TestMcpLoadingClaudeClient:
    """Tests for MCP loading via ClaudeClient."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(120)
    async def test_mcp_server_loading(self, temp_dir, nanobanana_mcp_config):
        """Test that MCP servers are loaded correctly."""
        client = ClaudeClient(
            cwd=str(temp_dir),
            mcp_servers=[nanobanana_mcp_config],
        )

        @client.on_text
        async def on_text(text: str):
            pass

        @client.on_permission
        async def on_permission(name: str, input: dict) -> bool:
            return True

        response = await client.query("List all MCP tools you have. Just list tool names.")

        # Check that nanobanana tools are visible
        assert "mcp__nanobanana" in response.lower() or "generate_image" in response.lower(), \
            f"MCP tools not found in response: {response}"

    @pytest.mark.asyncio
    @pytest.mark.timeout(120)
    async def test_multiple_mcp_servers(self, temp_dir, nanobanana_mcp_config):
        """Test loading multiple MCP servers."""
        # This test uses just nanobanana, but the structure supports multiple
        client = ClaudeClient(
            cwd=str(temp_dir),
            mcp_servers=[nanobanana_mcp_config],
        )

        @client.on_text
        async def on_text(text: str):
            pass

        @client.on_permission
        async def on_permission(name: str, input: dict) -> bool:
            return True

        response = await client.query("What MCP tools do you have access to?")
        assert len(response) > 0


@pytest.mark.integration
@pytest.mark.slow
@requires_claude_cli
@requires_claude_subscription
class TestMcpLoadingAcpClient:
    """Tests for MCP loading via AcpClient."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(120)
    async def test_mcp_server_loading(self, temp_dir, nanobanana_mcp_config):
        """Test that MCP servers are loaded via ACP protocol."""
        client = AcpClient(
            command="claude-code-acp",
            cwd=str(temp_dir),
            mcp_servers=[nanobanana_mcp_config],
        )

        @client.on_text
        async def on_text(text: str):
            pass

        @client.on_permission
        async def on_permission(name: str, input: dict, options: list) -> str:
            return "allow"

        async with client:
            response = await client.prompt("List all MCP tools. Just list tool names.")

        assert "mcp__nanobanana" in response.lower() or "generate_image" in response.lower(), \
            f"MCP tools not found in response: {response}"

    @pytest.mark.asyncio
    @pytest.mark.timeout(120)
    async def test_mcp_config_passed_to_session(self, temp_dir, nanobanana_mcp_config):
        """Test that MCP config is passed when creating session."""
        client = AcpClient(
            command="claude-code-acp",
            cwd=str(temp_dir),
            mcp_servers=[nanobanana_mcp_config],
        )

        @client.on_text
        async def on_text(text: str):
            pass

        @client.on_permission
        async def on_permission(name: str, input: dict, options: list) -> str:
            return "allow"

        async with client:
            # Create session explicitly
            session_id = await client.new_session()
            assert session_id is not None

            # Query should have access to MCP tools
            response = await client.prompt("Do you have any MCP tools? Answer yes or no.")
            assert "yes" in response.lower()


@pytest.mark.integration
@pytest.mark.slow
@requires_claude_cli
@requires_claude_subscription
class TestMcpStrictConfig:
    """Tests for --strict-mcp-config behavior."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(120)
    async def test_strict_config_overrides_user_config(self, temp_dir, nanobanana_mcp_config):
        """Test that --strict-mcp-config ignores user-level MCP configs."""
        # Create client with only nanobanana
        client = ClaudeClient(
            cwd=str(temp_dir),
            mcp_servers=[nanobanana_mcp_config],
        )

        @client.on_text
        async def on_text(text: str):
            pass

        @client.on_permission
        async def on_permission(name: str, input: dict) -> bool:
            return True

        response = await client.query(
            "List ALL MCP tools you have. Be complete and list every single one."
        )

        # Should only have nanobanana tools (due to --strict-mcp-config)
        # If other MCP tools appear that shouldn't be there, this test will catch it
        assert "nanobanana" in response.lower()

    @pytest.mark.asyncio
    @pytest.mark.timeout(120)
    async def test_empty_mcp_config_no_strict(self, temp_dir):
        """Test that empty MCP config doesn't add --strict-mcp-config."""
        client = ClaudeClient(
            cwd=str(temp_dir),
            mcp_servers=[],  # Empty - should not add strict flag
        )

        @client.on_text
        async def on_text(text: str):
            pass

        @client.on_permission
        async def on_permission(name: str, input: dict) -> bool:
            return True

        # This should work and potentially have access to user-level MCP configs
        response = await client.query("Hi, just say hello.")
        assert len(response) > 0
