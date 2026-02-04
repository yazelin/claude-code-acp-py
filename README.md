# Claude Code ACP (Python)

[![PyPI](https://img.shields.io/pypi/v/claude-code-acp)](https://pypi.org/project/claude-code-acp/)
[![Python](https://img.shields.io/pypi/pyversions/claude-code-acp)](https://pypi.org/project/claude-code-acp/)
[![License](https://img.shields.io/github/license/yazelin/claude-code-acp-py)](https://github.com/yazelin/claude-code-acp-py/blob/main/LICENSE)

**Python implementation of ACP (Agent Client Protocol) for Claude Code.**

This package bridges the [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python) with the [Agent Client Protocol (ACP)](https://agentclientprotocol.com/), providing two ways to use Claude:

1. **ACP Server** - Connect Claude to any ACP-compatible editor (Zed, Neovim, JetBrains, etc.)
2. **Python Client** - Event-driven API for building Python applications with Claude

## Features

- **Uses Claude CLI subscription** - No API key needed, uses your existing Claude subscription
- **Full ACP protocol support** - Compatible with Zed, Neovim, and other ACP clients
- **Bidirectional communication** - Permission requests, tool calls, streaming responses
- **Event-driven Python API** - Decorator-based handlers for easy integration
- **Session management** - Create, fork, resume, list sessions
- **Multiple permission modes** - default, acceptEdits, plan, bypassPermissions

## Installation

```bash
pip install claude-code-acp
```

Or with uv:

```bash
uv tool install claude-code-acp
```

## Requirements

- Python 3.10+
- Claude CLI installed and authenticated (`claude /login`)

---

## Components

| Class | Type | Description |
|-------|------|-------------|
| `ClaudeAcpAgent` | ACP Server | For editors (Zed, Neovim) to connect |
| `ClaudeClient` | Python API | Event-driven wrapper (uses agent internally) |
| `AcpClient` | ACP Client | Connect to any ACP agent via subprocess |

---

## Usage 1: ACP Server for Editors

Run as an ACP server to connect Claude to your editor:

```bash
claude-code-acp
```

### Zed Editor

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

Then open the Agent Panel (`Ctrl+?` / `Cmd+?`) and select "Claude Code Python" from the `+` menu.

### Other Editors

Any [ACP-compatible client](https://agentclientprotocol.com/overview/clients) can connect by spawning `claude-code-acp` as a subprocess and communicating via stdio.

---

## Usage 2: Python Event-Driven API

Use `ClaudeClient` for building Python applications with Claude:

```python
import asyncio
from claude_code_acp import ClaudeClient

async def main():
    client = ClaudeClient(cwd=".")

    @client.on_text
    async def handle_text(text: str):
        """Called for each text chunk from Claude."""
        print(text, end="", flush=True)

    @client.on_tool_start
    async def handle_tool_start(tool_id: str, name: str, input: dict):
        """Called when Claude starts using a tool."""
        print(f"\n🔧 {name}")

    @client.on_tool_end
    async def handle_tool_end(tool_id: str, status: str, output):
        """Called when a tool completes."""
        icon = "✅" if status == "completed" else "❌"
        print(f" {icon}")

    @client.on_permission
    async def handle_permission(name: str, input: dict) -> bool:
        """Called when Claude needs permission. Return True to allow."""
        print(f"🔐 Permission requested: {name}")
        return True  # or prompt user

    @client.on_complete
    async def handle_complete():
        """Called when the query completes."""
        print("\n--- Done ---")

    # Send a query
    response = await client.query("Create a hello.py file that prints Hello World")
    print(f"\nFull response: {response}")

asyncio.run(main())
```

### Event Handlers

| Decorator | Arguments | Description |
|-----------|-----------|-------------|
| `@client.on_text` | `(text: str)` | Streaming text chunks from Claude |
| `@client.on_thinking` | `(text: str)` | Thinking/reasoning blocks |
| `@client.on_tool_start` | `(tool_id, name, input)` | Tool execution started |
| `@client.on_tool_end` | `(tool_id, status, output)` | Tool execution completed |
| `@client.on_permission` | `(name, input) -> bool` | Permission request (return True/False) |
| `@client.on_error` | `(exception)` | Error occurred |
| `@client.on_complete` | `()` | Query completed |

### Client Methods

```python
# Start a new session
session_id = await client.start_session()

# Send a query (returns full response text)
response = await client.query("Your prompt here")

# Set permission mode
await client.set_mode("acceptEdits")  # or "default", "plan", "bypassPermissions"
```

---

## Usage 3: ACP Client (Connect to Any Agent)

Use `AcpClient` to connect to any ACP-compatible agent:

```python
import asyncio
from claude_code_acp import AcpClient

async def main():
    # Connect to claude-code-acp (Python version)
    client = AcpClient(command="claude-code-acp")

    # Or connect to the TypeScript version
    # client = AcpClient(command="npx", args=["@zed-industries/claude-code-acp"])

    # Or any other ACP agent
    # client = AcpClient(command="my-custom-agent")

    @client.on_text
    async def handle_text(text: str):
        print(text, end="", flush=True)

    @client.on_tool_start
    async def handle_tool(tool_id: str, name: str, input: dict):
        print(f"\n🔧 {name}")

    @client.on_permission
    async def handle_permission(name: str, input: dict, options: list) -> str:
        """Return option_id: 'allow', 'reject', or 'allow_always'"""
        print(f"🔐 Permission: {name}")
        return "allow"

    @client.on_complete
    async def handle_complete():
        print("\n--- Done ---")

    async with client:
        response = await client.prompt("What files are here?")

asyncio.run(main())
```

### AcpClient vs ClaudeClient

| Feature | `ClaudeClient` | `AcpClient` |
|---------|---------------|-------------|
| Uses | Claude Agent SDK directly | Any ACP agent via subprocess |
| Connection | In-process | Subprocess + stdio |
| Agents | Claude only | Any ACP-compatible agent |
| Use case | Simple Python apps | Multi-agent, testing, flexibility |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Your Application                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐                      ┌─────────────────────────────┐  │
│  │   Zed/Neovim    │                      │     Python Application      │  │
│  │   (ACP Client)  │                      │                             │  │
│  └────────┬────────┘                      │  client = ClaudeClient()    │  │
│           │                               │                             │  │
│           │ ACP Protocol                  │  @client.on_text            │  │
│           │ (stdio/JSON-RPC)              │  async def handle(text):    │  │
│           │                               │      print(text)            │  │
│           ▼                               │                             │  │
│  ┌────────────────────────────────────────┴─────────────────────────────┐  │
│  │                                                                       │  │
│  │                      claude-code-acp (This Package)                   │  │
│  │                                                                       │  │
│  │   ┌─────────────────────┐      ┌─────────────────────────────────┐   │  │
│  │   │   ClaudeAcpAgent    │      │        ClaudeClient             │   │  │
│  │   │   (ACP Server)      │      │    (Event-driven wrapper)       │   │  │
│  │   └──────────┬──────────┘      └───────────────┬─────────────────┘   │  │
│  │              │                                 │                      │  │
│  │              └────────────────┬────────────────┘                      │  │
│  │                               │                                       │  │
│  └───────────────────────────────┼───────────────────────────────────────┘  │
│                                  │                                          │
│                                  ▼                                          │
│                    ┌─────────────────────────────┐                          │
│                    │    Claude Agent SDK         │                          │
│                    │    (claude-agent-sdk)       │                          │
│                    └──────────────┬──────────────┘                          │
│                                   │                                         │
│                                   ▼                                         │
│                    ┌─────────────────────────────┐                          │
│                    │       Claude CLI            │                          │
│                    │  (Your Claude Subscription) │                          │
│                    └─────────────────────────────┘                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## What We Built

This project combines two official SDKs to create a complete Python solution:

### Integrated Components

| Component | Source | Purpose |
|-----------|--------|---------|
| [Agent Client Protocol SDK](https://github.com/anthropics/agent-client-protocol) | Anthropic | ACP server/client protocol implementation |
| [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python) | Anthropic | Claude CLI wrapper with streaming support |

### Our Contributions

1. **ClaudeAcpAgent** (`agent.py`)
   - Bridges Claude Agent SDK with ACP protocol
   - Converts Claude messages to ACP session updates
   - Handles bidirectional permission requests
   - Session management (create, fork, resume, list)

2. **ClaudeClient** (`client.py`)
   - Event-driven Python API with decorators
   - Smart text deduplication for streaming
   - Simple permission handling
   - Clean async/await interface

3. **ACP Server Entry Point**
   - Standalone `claude-code-acp` command
   - Direct integration with Zed and other ACP clients
   - No configuration needed

### Why This Package?

| Approach | API Key | Subscription | ACP Support | Event-Driven |
|----------|---------|--------------|-------------|--------------|
| Anthropic API directly | ✅ Required | ❌ | ❌ | ❌ |
| Claude Agent SDK | ❌ | ✅ Uses CLI | ❌ | Partial |
| **claude-code-acp** | ❌ | ✅ Uses CLI | ✅ Full | ✅ Full |

---

## Examples

### Simple Chat

```python
import asyncio
from claude_code_acp import ClaudeClient

async def main():
    client = ClaudeClient()

    @client.on_text
    async def on_text(text):
        print(text, end="")

    while True:
        user_input = input("\nYou: ")
        if user_input.lower() == "quit":
            break
        await client.query(user_input)

asyncio.run(main())
```

### File Operations with Permission Control

```python
import asyncio
from claude_code_acp import ClaudeClient

async def main():
    client = ClaudeClient(cwd="/path/to/project")

    @client.on_text
    async def on_text(text):
        print(text, end="")

    @client.on_permission
    async def on_permission(name, input):
        response = input(f"Allow '{name}'? [y/N]: ")
        return response.lower() == "y"

    await client.query("Refactor the main.py file to use async/await")

asyncio.run(main())
```

### Auto-approve Mode

```python
import asyncio
from claude_code_acp import ClaudeClient

async def main():
    client = ClaudeClient(cwd=".")

    # Bypass all permission checks
    await client.set_mode("bypassPermissions")

    @client.on_text
    async def on_text(text):
        print(text, end="")

    await client.query("Create a complete Flask app with tests")

asyncio.run(main())
```

---

## Development

```bash
# Clone
git clone https://github.com/yazelin/claude-code-acp-py
cd claude-code-acp-py

# Install dependencies
uv sync

# Run locally
uv run claude-code-acp

# Run tests
uv run python -c "from claude_code_acp import ClaudeClient; print('OK')"
```

---

## Related Projects

- [claude-code-acp](https://github.com/zed-industries/claude-code-acp) - TypeScript version by Zed Industries
- [agent-client-protocol](https://github.com/anthropics/agent-client-protocol) - ACP specification and SDKs
- [claude-agent-sdk-python](https://github.com/anthropics/claude-agent-sdk-python) - Official Claude Agent SDK

---

## License

MIT
