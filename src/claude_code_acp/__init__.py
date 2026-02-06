"""
Claude Code ACP - ACP-compatible agent for Claude Code (Python version).

This package bridges the Claude Agent SDK with the Agent Client Protocol (ACP),
allowing Claude Code to work with any ACP-compatible client like Zed, Neovim, etc.
"""

import asyncio

from .agent import ClaudeAcpAgent
from .client import ClaudeClient, ClaudeEvents
from .acp_client import AcpClient, AcpClientEvents

__version__ = "0.4.1"

__all__ = [
    "ClaudeAcpAgent",
    "ClaudeClient",
    "ClaudeEvents",
    "AcpClient",
    "AcpClientEvents",
    "main",
    "run",
]


async def run() -> None:
    """Run the Claude ACP agent."""
    from acp import run_agent
    # Enable unstable protocol to support set_session_model
    await run_agent(ClaudeAcpAgent(), use_unstable_protocol=True)


def main() -> None:
    """Entry point for the claude-code-acp command."""
    asyncio.run(run())


if __name__ == "__main__":
    main()
