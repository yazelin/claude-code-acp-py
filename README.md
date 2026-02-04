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

### Connect to Different Agents

```python
from claude_code_acp import AcpClient

# Connect to our Claude ACP server
claude = AcpClient(command="claude-code-acp")

# Connect to Gemini CLI
gemini = AcpClient(command="gemini", args=["--experimental-acp"])

# Connect to TypeScript version
ts_claude = AcpClient(command="npx", args=["@zed-industries/claude-code-acp"])
```

### File Operation Handlers

AcpClient supports intercepting file read/write operations for security or custom handling:

```python
@client.on_file_read
async def handle_read(path: str) -> str | None:
    """Intercept file reads. Return content to override, or None to proceed."""
    print(f"📖 Reading: {path}")
    return None  # Proceed with normal read

@client.on_file_write
async def handle_write(path: str, content: str) -> bool:
    """Intercept file writes. Return True to allow, False to block."""
    print(f"📝 Writing: {path}")
    response = input("Allow write? [y/N]: ")
    return response.lower() == "y"
```

### Terminal Operation Handlers

AcpClient supports intercepting terminal/shell execution for security:

```python
@client.on_terminal_create
async def handle_terminal(command: str, cwd: str) -> bool:
    """Intercept shell commands. Return True to allow, False to block."""
    print(f"🖥️ Command: {command} in {cwd}")
    response = input("Allow execution? [y/N]: ")
    return response.lower() == "y"

@client.on_terminal_output
async def handle_output(terminal_id: str, output: str) -> None:
    """Receive terminal output in real-time."""
    print(output, end="")
```

### AcpClient vs ClaudeClient

| Feature | `ClaudeClient` | `AcpClient` |
|---------|---------------|-------------|
| Uses | Claude Agent SDK directly | Any ACP agent via subprocess |
| Connection | In-process | Subprocess + stdio |
| Agents | Claude only | Any ACP-compatible agent |
| Use case | Simple Python apps | Multi-agent, testing, flexibility |

### Tested Agents

| Agent | Command | Status |
|-------|---------|--------|
| claude-code-acp (this package) | `claude-code-acp` | ✅ Works |
| Gemini CLI | `gemini --experimental-acp` | ✅ Works |
| TypeScript version | `npx @zed-industries/claude-code-acp` | ✅ Compatible |

### Gemini ACP Usage

**Important:** Gemini takes ~12 seconds to initialize on first connection.

```python
import asyncio
from claude_code_acp import AcpClient

async def main():
    client = AcpClient(
        command="gemini",
        args=["--experimental-acp"],
        cwd="/tmp",
    )

    @client.on_text
    async def on_text(text):
        print(text, end="", flush=True)

    @client.on_thinking
    async def on_thinking(text):
        print(f"[Thinking] {text[:50]}...")

    # Note: connect() takes ~12s for Gemini initialization
    async with client:
        response = await client.prompt("Hello!")
        print(f"\nResponse: {response}")

asyncio.run(main())
```

### Gemini with MCP Servers

Gemini requires MCP servers to be **pre-configured** via CLI (not via ACP protocol):

```bash
# 1. Add MCP server to Gemini config
gemini mcp add nanobanana "uvx nanobanana"

# 2. Verify it's configured
gemini mcp list
```

Then use `--allowed-mcp-server-names` to enable it:

```python
import asyncio
from claude_code_acp import AcpClient

async def main():
    client = AcpClient(
        command="gemini",
        args=[
            "--experimental-acp",
            "--allowed-mcp-server-names", "nanobanana",  # Enable MCP server
        ],
        cwd="/tmp",
    )

    @client.on_text
    async def on_text(text):
        print(text, end="", flush=True)

    async with client:
        # Now Gemini can use nanobanana MCP tools
        response = await client.prompt("Generate an image of a red circle")
        print(f"\nResponse: {response}")

asyncio.run(main())
```

### MCP Configuration Comparison

| Agent | Dynamic MCP (via ACP) | Pre-configured MCP |
|-------|----------------------|-------------------|
| claude-code-acp | ✅ Supported | ✅ Supported |
| Gemini CLI | ❌ Not supported | ✅ Use `--allowed-mcp-server-names` |

**claude-code-acp** supports dynamic MCP configuration:

```python
client = AcpClient(
    command="claude-code-acp",
    cwd="/tmp",
    mcp_servers=[{
        "name": "nanobanana",
        "command": "uvx",
        "args": ["nanobanana"],
        "env": {"GEMINI_API_KEY": "your-key"},
    }],
)
```

---

## Architecture

This package provides **three ways** to use Claude:

### Method A: Editor via ACP (ClaudeAcpAgent)

For Zed, Neovim, and other ACP-compatible editors:

```
┌──────────┐      ACP Protocol      ┌─────────────────┐      SDK      ┌────────────┐
│   Zed    │ ────── stdio ───────►  │ ClaudeAcpAgent  │ ──────────►   │ Claude CLI │
│  Editor  │                        │  (ACP Server)   │               │            │
└──────────┘                        └─────────────────┘               └────────────┘
```

### Method B: Python Direct (ClaudeClient)

For Python apps that want simple, direct access to Claude (**no ACP protocol**):

```
┌──────────┐     direct call      ┌─────────────────┐      SDK      ┌────────────┐
│  Python  │ ──── in-process ───► │  ClaudeClient   │ ──────────►   │ Claude CLI │
│   App    │                      │                 │               │            │
└──────────┘                      └─────────────────┘               └────────────┘
```

### Method C: Python via ACP (AcpClient)

For Python apps that want to connect to **any** ACP-compatible agent:

```
┌──────────┐      ACP Protocol      ┌─────────────────┐
│  Python  │ ────── stdio ───────►  │  Any ACP Agent  │
│   App    │                        │                 │
│          │                        │ • claude-code   │
│ AcpClient│                        │ • gemini        │
│          │                        │ • custom agents │
└──────────┘                        └─────────────────┘
```

### Summary

| Component | Uses ACP? | Purpose |
|-----------|-----------|---------|
| `ClaudeAcpAgent` | Yes (Server) | Let editors connect to Claude |
| `ClaudeClient` | **No** | Simplest way for Python apps |
| `AcpClient` | Yes (Client) | Connect to any ACP agent |

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
