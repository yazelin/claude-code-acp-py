"""Pytest configuration and shared fixtures."""

import os
import sys
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# --- Fixtures ---


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for tests."""
    return tmp_path


@pytest.fixture
def sample_mcp_config():
    """Sample MCP server configuration for testing."""
    return {
        "name": "test-server",
        "command": "echo",
        "args": ["hello"],
        "env": {},
    }


@pytest.fixture
def nanobanana_mcp_config():
    """Real nanobanana MCP server configuration (requires nanobanana installed)."""
    # Check if nanobanana environment file exists
    env_file = Path.home() / "gemini" / ".env"
    nanobanana_dir = Path.home() / "SDD" / "nanobanana-py"

    if not env_file.exists() or not nanobanana_dir.exists():
        pytest.skip("Nanobanana environment not configured")

    return {
        "name": "nanobanana",
        "command": "bash",
        "args": [
            "-c",
            f"set -a && source {env_file} && set +a && uv run --directory {nanobanana_dir} nanobanana-py",
        ],
    }


# --- Markers ---


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests (fast, no external dependencies)")
    config.addinivalue_line("markers", "integration: Integration tests (require Claude CLI)")
    config.addinivalue_line("markers", "slow: Slow tests (MCP loading, etc.)")


# --- Skip conditions ---


def is_claude_cli_available() -> bool:
    """Check if Claude CLI is available."""
    try:
        import shutil
        from pathlib import Path

        # Check bundled CLI first
        try:
            from claude_agent_sdk._internal.transport.subprocess_cli import SubprocessCLITransport

            transport = SubprocessCLITransport.__new__(SubprocessCLITransport)
            bundled = transport._find_bundled_cli()
            if bundled:
                return True
        except Exception:
            pass

        # Check system-wide CLI
        if shutil.which("claude"):
            return True

        # Check common locations
        locations = [
            Path.home() / ".npm-global/bin/claude",
            Path("/usr/local/bin/claude"),
            Path.home() / ".local/bin/claude",
            Path.home() / ".claude/local/claude",
        ]
        return any(p.exists() for p in locations)
    except Exception:
        return False


def has_claude_subscription() -> bool:
    """Check if user has Claude subscription (can make API calls)."""
    # This is a simple heuristic - check if .claude directory exists
    return (Path.home() / ".claude").exists()


# Skip decorators for use in tests
requires_claude_cli = pytest.mark.skipif(
    not is_claude_cli_available(),
    reason="Claude CLI not available",
)

requires_claude_subscription = pytest.mark.skipif(
    not has_claude_subscription(),
    reason="Claude subscription required",
)
