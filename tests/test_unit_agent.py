"""Unit tests for ClaudeAcpAgent."""

import pytest

from claude_code_acp.agent import ClaudeAcpAgent, Session


class TestSession:
    """Tests for Session dataclass."""

    def test_session_creation(self):
        """Test creating a session with default values."""
        session = Session(session_id="test-123", cwd="/tmp")

        assert session.session_id == "test-123"
        assert session.cwd == "/tmp"
        assert session.permission_mode == "default"
        assert session.cancelled is False
        assert session.tool_use_cache == {}
        assert session.mcp_servers == {}
        assert session.system_prompt is None
        assert session.model is None
        assert session.client is None
        assert session.client_started is False
        assert session.streamed_text == ""

    def test_session_with_custom_values(self):
        """Test creating a session with custom values."""
        mcp_servers = {"test": {"type": "stdio", "command": "echo"}}
        session = Session(
            session_id="test-456",
            cwd="/home/user",
            permission_mode="bypassPermissions",
            mcp_servers=mcp_servers,
            system_prompt="Custom prompt",
            model="sonnet",
        )

        assert session.session_id == "test-456"
        assert session.permission_mode == "bypassPermissions"
        assert session.mcp_servers == mcp_servers
        assert session.system_prompt == "Custom prompt"
        assert session.model == "sonnet"


class TestClaudeAcpAgent:
    """Tests for ClaudeAcpAgent."""

    def test_agent_initialization(self):
        """Test agent initialization."""
        agent = ClaudeAcpAgent()

        assert agent._conn is None
        assert agent._sessions == {}

    def test_convert_prompt_to_text_simple(self):
        """Test converting simple text prompt."""
        agent = ClaudeAcpAgent()

        # Test with dict-style text block
        prompt = [{"type": "text", "text": "Hello, world!"}]
        result = agent._convert_prompt_to_text(prompt)

        assert result == "Hello, world!"

    def test_convert_prompt_to_text_multiple(self):
        """Test converting multiple text blocks."""
        agent = ClaudeAcpAgent()

        prompt = [
            {"type": "text", "text": "First line"},
            {"type": "text", "text": "Second line"},
        ]
        result = agent._convert_prompt_to_text(prompt)

        assert "First line" in result
        assert "Second line" in result

    def test_convert_prompt_to_text_with_resource(self):
        """Test converting prompt with resource blocks."""
        agent = ClaudeAcpAgent()

        prompt = [
            {"type": "text", "text": "Check this:"},
            {
                "type": "resource",
                "resource": {
                    "uri": "file:///test.txt",
                    "text": "File content here",
                },
            },
        ]
        result = agent._convert_prompt_to_text(prompt)

        assert "Check this:" in result
        assert "file:///test.txt" in result
        assert "File content here" in result

    def test_convert_mcp_servers_stdio(self):
        """Test converting stdio MCP server config."""
        agent = ClaudeAcpAgent()

        # Test with dict-style config
        servers = [
            {
                "type": "stdio",
                "name": "test-server",
                "command": "echo",
                "args": ["hello"],
                "env": {"KEY": "value"},
            }
        ]
        result = agent._convert_mcp_servers(servers)

        assert "test-server" in result
        assert result["test-server"]["type"] == "stdio"
        assert result["test-server"]["command"] == "echo"
        assert result["test-server"]["args"] == ["hello"]
        assert result["test-server"]["env"] == {"KEY": "value"}

    def test_convert_mcp_servers_empty(self):
        """Test converting empty MCP server list."""
        agent = ClaudeAcpAgent()

        result = agent._convert_mcp_servers([])

        assert result == {}

    def test_get_tool_title_read(self):
        """Test generating tool title for Read tool."""
        agent = ClaudeAcpAgent()

        title = agent._get_tool_title("Read", {"file_path": "/home/test/file.py"})

        assert title == "Read /home/test/file.py"

    def test_get_tool_title_write(self):
        """Test generating tool title for Write tool."""
        agent = ClaudeAcpAgent()

        title = agent._get_tool_title("Write", {"file_path": "/home/test/new.py"})

        assert title == "Write /home/test/new.py"

    def test_get_tool_title_bash(self):
        """Test generating tool title for Bash tool."""
        agent = ClaudeAcpAgent()

        # Short command
        title = agent._get_tool_title("Bash", {"command": "ls -la"})
        assert title == "Run: ls -la"

        # Long command (truncated)
        long_cmd = "a" * 100
        title = agent._get_tool_title("Bash", {"command": long_cmd})
        assert len(title) < len(long_cmd) + 10
        assert "..." in title

    def test_get_tool_title_glob(self):
        """Test generating tool title for Glob tool."""
        agent = ClaudeAcpAgent()

        title = agent._get_tool_title("Glob", {"pattern": "**/*.py"})

        assert title == "Find files: **/*.py"

    def test_get_tool_title_grep(self):
        """Test generating tool title for Grep tool."""
        agent = ClaudeAcpAgent()

        title = agent._get_tool_title("Grep", {"pattern": "def main"})

        assert title == "Search: def main"

    def test_get_tool_title_unknown(self):
        """Test generating tool title for unknown tool."""
        agent = ClaudeAcpAgent()

        title = agent._get_tool_title("UnknownTool", {"arg": "value"})

        assert title == "UnknownTool"


class TestAgentAsyncMethods:
    """Tests for async methods of ClaudeAcpAgent."""

    @pytest.mark.asyncio
    async def test_initialize_response(self):
        """Test initialize returns proper response."""
        agent = ClaudeAcpAgent()

        response = await agent.initialize(
            protocol_version=1,
            client_capabilities=None,
            client_info=None,
        )

        assert response.protocol_version == 1
        assert response.agent_info.name == "claude-code-acp-py"
        assert response.agent_capabilities is not None

    @pytest.mark.asyncio
    async def test_new_session_creates_session(self):
        """Test new_session creates and stores a session."""
        agent = ClaudeAcpAgent()

        response = await agent.new_session(
            cwd="/tmp",
            mcp_servers=[],
        )

        assert response.session_id is not None
        assert response.session_id in agent._sessions
        assert agent._sessions[response.session_id].cwd == "/tmp"

    @pytest.mark.asyncio
    async def test_new_session_with_mcp_servers(self):
        """Test new_session with MCP servers."""
        agent = ClaudeAcpAgent()

        mcp_servers = [
            {
                "type": "stdio",
                "name": "test",
                "command": "echo",
                "args": [],
                "env": {},
            }
        ]

        response = await agent.new_session(
            cwd="/tmp",
            mcp_servers=mcp_servers,
        )

        session = agent._sessions[response.session_id]
        assert "test" in session.mcp_servers

    @pytest.mark.asyncio
    async def test_set_session_mode_valid(self):
        """Test setting valid permission mode."""
        agent = ClaudeAcpAgent()

        # Create a session first
        session_response = await agent.new_session(cwd="/tmp", mcp_servers=[])
        session_id = session_response.session_id

        # Set mode
        await agent.set_session_mode(mode_id="bypassPermissions", session_id=session_id)

        assert agent._sessions[session_id].permission_mode == "bypassPermissions"

    @pytest.mark.asyncio
    async def test_set_session_mode_invalid_session(self):
        """Test setting mode for non-existent session."""
        agent = ClaudeAcpAgent()

        with pytest.raises(ValueError, match="Session not found"):
            await agent.set_session_mode(mode_id="default", session_id="non-existent")

    @pytest.mark.asyncio
    async def test_set_session_mode_invalid_mode(self):
        """Test setting invalid permission mode."""
        agent = ClaudeAcpAgent()

        session_response = await agent.new_session(cwd="/tmp", mcp_servers=[])

        with pytest.raises(ValueError, match="Invalid mode"):
            await agent.set_session_mode(mode_id="invalid_mode", session_id=session_response.session_id)

    @pytest.mark.asyncio
    async def test_cancel_session(self):
        """Test cancelling a session."""
        agent = ClaudeAcpAgent()

        session_response = await agent.new_session(cwd="/tmp", mcp_servers=[])
        session_id = session_response.session_id

        await agent.cancel(session_id=session_id)

        assert agent._sessions[session_id].cancelled is True

    @pytest.mark.asyncio
    async def test_list_sessions(self):
        """Test listing sessions."""
        agent = ClaudeAcpAgent()

        # Create multiple sessions
        await agent.new_session(cwd="/tmp", mcp_servers=[])
        await agent.new_session(cwd="/home", mcp_servers=[])

        response = await agent.list_sessions()

        assert len(response.sessions) == 2

    @pytest.mark.asyncio
    async def test_list_sessions_filter_by_cwd(self):
        """Test listing sessions filtered by cwd."""
        agent = ClaudeAcpAgent()

        await agent.new_session(cwd="/tmp", mcp_servers=[])
        await agent.new_session(cwd="/home", mcp_servers=[])

        response = await agent.list_sessions(cwd="/tmp")

        assert len(response.sessions) == 1
        assert response.sessions[0].cwd == "/tmp"

    @pytest.mark.asyncio
    async def test_fork_session(self):
        """Test forking a session."""
        agent = ClaudeAcpAgent()

        original = await agent.new_session(cwd="/tmp", mcp_servers=[])
        await agent.set_session_mode(mode_id="acceptEdits", session_id=original.session_id)

        forked = await agent.fork_session(cwd="/home", session_id=original.session_id)

        assert forked.session_id != original.session_id
        assert forked.session_id in agent._sessions
        # Forked session inherits permission mode
        assert agent._sessions[forked.session_id].permission_mode == "acceptEdits"
        assert agent._sessions[forked.session_id].cwd == "/home"

    @pytest.mark.asyncio
    async def test_fork_session_invalid(self):
        """Test forking non-existent session."""
        agent = ClaudeAcpAgent()

        with pytest.raises(ValueError, match="Session not found"):
            await agent.fork_session(cwd="/home", session_id="non-existent")

    @pytest.mark.asyncio
    async def test_set_session_model(self):
        """Test setting model for a session."""
        agent = ClaudeAcpAgent()

        session = await agent.new_session(cwd="/tmp", mcp_servers=[])

        await agent.set_session_model(model_id="opus", session_id=session.session_id)

        assert agent._sessions[session.session_id].model == "opus"
