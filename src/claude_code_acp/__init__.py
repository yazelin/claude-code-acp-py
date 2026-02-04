"""
Claude Code ACP - ACP-compatible agent for Claude Code (Python version).

This package bridges the Claude Agent SDK with the Agent Client Protocol (ACP),
allowing Claude Code to work with any ACP-compatible client like Zed, Neovim, etc.
"""

import asyncio

from .agent import ClaudeAcpAgent

__version__ = "0.1.0"

__all__ = ["ClaudeAcpAgent", "main", "run"]


async def run() -> None:
    """Run the Claude ACP agent."""
    from acp import run_agent
    await run_agent(ClaudeAcpAgent())


def main() -> None:
    """Entry point for the claude-code-acp command."""
    asyncio.run(run())


if __name__ == "__main__":
    main()
