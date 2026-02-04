# Claude Code ACP (Python)

[![PyPI](https://img.shields.io/pypi/v/claude-code-acp)](https://pypi.org/project/claude-code-acp/)
[![Python](https://img.shields.io/pypi/pyversions/claude-code-acp)](https://pypi.org/project/claude-code-acp/)
[![License](https://img.shields.io/github/license/yazelin/claude-code-acp-py)](https://github.com/yazelin/claude-code-acp-py/blob/main/LICENSE)

ACP-compatible agent for Claude Code using the Python SDK.

This package bridges the [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python) with the [Agent Client Protocol (ACP)](https://agentclientprotocol.com/), allowing Claude Code to work with any ACP-compatible client like [Zed](https://zed.dev), Neovim, JetBrains IDEs, etc.

## Features

- Full ACP protocol support
- Bidirectional communication (permission requests, tool calls)
- Uses your Claude CLI subscription (no API key needed)
- Session management (create, fork, resume, list)
- Multiple permission modes (default, acceptEdits, plan, bypassPermissions)

## Installation

```bash
pip install claude-code-acp
```

Or with uv:

```bash
uv add claude-code-acp
```

## Requirements

- Python 3.10+
- Claude CLI installed and authenticated (`claude /login`)

## Usage

### As a standalone ACP server

```bash
claude-code-acp
```

### With Zed Editor

Add to your Zed `settings.json`:

```json
{
  "agent_servers": {
    "Claude Code Python": {
      "type": "custom",
      "command": "claude-code-acp",
      "args": [],
      "env": {}
    }
  }
}
```

Then open the Agent Panel (`Ctrl+?`) and select "Claude Code Python" from the `+` menu.

### As a library

```python
import asyncio
from claude_code_acp import ClaudeAcpAgent
from acp import run_agent

async def main():
    agent = ClaudeAcpAgent()
    await run_agent(agent)

asyncio.run(main())
```

## How it works

```
┌─────────────┐     ACP      ┌──────────────────┐    SDK     ┌─────────────┐
│  Zed/IDE    │ ◄──────────► │ claude-code-acp  │ ◄────────► │ Claude CLI  │
│ (ACP Client)│   (stdio)    │  (This package)  │            │(Subscription)│
└─────────────┘              └──────────────────┘            └─────────────┘
```

## License

MIT
