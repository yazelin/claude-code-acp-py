# Claude Code ACP (Python)

[![PyPI](https://img.shields.io/pypi/v/claude-code-acp)](https://pypi.org/project/claude-code-acp/)
[![Python](https://img.shields.io/pypi/pyversions/claude-code-acp)](https://pypi.org/project/claude-code-acp/)
[![License](https://img.shields.io/github/license/yazelin/claude-code-acp-py)](https://github.com/yazelin/claude-code-acp-py/blob/main/LICENSE)

**Python implementation of ACP (Agent Client Protocol) for Claude Code.**

This package combines the [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python) with the [Agent Client Protocol (ACP)](https://agentclientprotocol.com/) to provide a complete Python solution for working with AI agents.

## What It Does

| Component | Type | Description |
|-----------|------|-------------|
| `ClaudeAcpAgent` | ACP Server | Lets editors (Zed, Neovim, JetBrains) use Claude |
| `ClaudeClient` | Python API | Event-driven wrapper for building Python apps with Claude |
| `AcpClient` | ACP Client | Connect to **any** ACP-compatible agent (Claude, Gemini, custom) |
| `AcpProxyServer` | Copilot Proxy | Bridge Copilot SDK to any ACP backend |

Two CLI commands:
- **`claude-code-acp`** - ACP server for editors
- **`copilot-acp-proxy`** - Copilot SDK proxy to ACP backends

## Features

- **Uses Claude CLI subscription** - No API key needed
- **Full ACP protocol** - Compatible with Zed, Neovim, and other ACP clients
- **Universal ACP client** - Connect to any ACP agent (Claude, Gemini, or custom)
- **Copilot SDK bridge** - Use Copilot SDK with any ACP backend
- **Bidirectional communication** - Permission requests, tool calls, streaming
- **Event-driven Python API** - Decorator-based handlers
- **Session management** - Create, fork, resume, list sessions
- **MCP server support** - Dynamic loading via stdio, HTTP, SSE
- **Model & command enumeration** - Discover available models and commands at runtime

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

## Usage 1: ACP Server for Editors

Run as an ACP server so editors can use Claude:

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
    client = ClaudeClient(cwd=".", system_prompt="You are a helpful assistant.")

    @client.on_text
    async def handle_text(text: str):
        print(text, end="", flush=True)

    @client.on_tool_start
    async def handle_tool_start(tool_id: str, name: str, input: dict):
        print(f"\n[Tool] {name}")

    @client.on_tool_end
    async def handle_tool_end(tool_id: str, status: str, output):
        icon = "ok" if status == "completed" else "fail"
        print(f" [{icon}]")

    @client.on_permission
    async def handle_permission(name: str, input: dict) -> bool:
        print(f"Permission requested: {name}")
        return True  # or prompt user

    @client.on_complete
    async def handle_complete():
        print("\n--- Done ---")

    response = await client.query("Create a hello.py file that prints Hello World")
    print(f"\nFull response: {response}")

asyncio.run(main())
```

### Event Handlers

| Decorator | Arguments | Description |
|-----------|-----------|-------------|
| `@client.on_text` | `(text: str)` | Streaming text chunks |
| `@client.on_thinking` | `(text: str)` | Thinking/reasoning blocks |
| `@client.on_tool_start` | `(tool_id, name, input)` | Tool execution started |
| `@client.on_tool_end` | `(tool_id, status, output)` | Tool execution completed |
| `@client.on_permission` | `(name, input) -> bool` | Permission request (return True/False) |
| `@client.on_error` | `(exception)` | Error occurred |
| `@client.on_complete` | `()` | Query completed |

### Client Methods

```python
# Init with optional MCP servers and system prompt
client = ClaudeClient(cwd=".", mcp_servers=[...], system_prompt="...")

# Start a new session
session_id = await client.start_session()

# Send a query (returns full response text)
response = await client.query("Your prompt here")

# Set permission mode
await client.set_mode("acceptEdits")  # or "default", "plan", "bypassPermissions"
```

---

## Usage 3: ACP Client (Connect to Any Agent)

Since this package implements a full ACP client, you can use `AcpClient` to connect to **any** ACP-compatible agent - not just Claude.

```python
import asyncio
from claude_code_acp import AcpClient

async def main():
    # Connect to any ACP agent
    client = AcpClient(command="claude-code-acp")

    @client.on_text
    async def handle_text(text: str):
        print(text, end="", flush=True)

    @client.on_tool_start
    async def handle_tool(tool_id: str, name: str, input: dict):
        print(f"\n[Tool] {name}")

    @client.on_permission
    async def handle_permission(name: str, input: dict, options: list) -> str:
        """Return option_id: 'allow', 'reject', or 'allow_always'"""
        print(f"Permission: {name}")
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

# Claude (this package)
claude = AcpClient(command="claude-code-acp")

# Gemini CLI
gemini = AcpClient(command="gemini", args=["--experimental-acp"])

# TypeScript version
ts_claude = AcpClient(command="npx", args=["@zed-industries/claude-code-acp"])

# Any custom ACP agent
custom = AcpClient(command="my-custom-agent")
```

### Tested Agents

| Agent | Command | Status |
|-------|---------|--------|
| claude-code-acp (this package) | `claude-code-acp` | Works |
| Gemini CLI | `gemini --experimental-acp` | Works |
| TypeScript version | `npx @zed-industries/claude-code-acp` | Compatible |

### File Operation Handlers

Intercept file read/write operations for security or custom handling:

```python
@client.on_file_read
async def handle_read(path: str) -> str | None:
    """Return content to override, or None to proceed normally."""
    print(f"Reading: {path}")
    return None

@client.on_file_write
async def handle_write(path: str, content: str) -> bool:
    """Return True to allow, False to block."""
    print(f"Writing: {path}")
    return input("Allow? [y/N]: ").lower() == "y"
```

### Terminal Operation Handlers

Intercept shell execution for security:

```python
@client.on_terminal_create
async def handle_terminal(command: str, cwd: str) -> bool:
    """Return True to allow, False to block."""
    print(f"Command: {command} in {cwd}")
    return input("Allow? [y/N]: ").lower() == "y"

@client.on_terminal_output
async def handle_output(terminal_id: str, output: str) -> None:
    print(output, end="")
```

### Model Selection

```python
# Set model before connecting (pending)
client = AcpClient(command="claude-code-acp")
client.set_model("opus")  # Will be applied when session starts

# Or set model on active session
async with client:
    await client.set_model("sonnet")
    response = await client.prompt("Hello!")
```

### AcpClient vs ClaudeClient

| Feature | `ClaudeClient` | `AcpClient` |
|---------|---------------|-------------|
| Uses | Claude Agent SDK directly | Any ACP agent via subprocess |
| Connection | In-process | Subprocess + stdio |
| Agents | Claude only | Any ACP-compatible agent |
| File/Terminal hooks | No | Yes |
| Use case | Simple Python apps | Multi-agent, testing, flexibility |

---

## Usage 4: Copilot SDK Proxy

The `copilot-acp-proxy` command bridges the Copilot SDK to any ACP backend, allowing Copilot SDK applications to use Claude, Gemini, or other ACP agents.

```bash
# Connect Copilot SDK to Gemini
copilot-acp-proxy --headless --stdio --backend gemini

# Connect Copilot SDK to Claude
copilot-acp-proxy --headless --stdio --backend claude-code-acp

# Connect Copilot SDK to Copilot CLI
copilot-acp-proxy --headless --stdio --backend copilot
```

### Proxy with Copilot SDK (Python)

```python
import asyncio
from copilot import CopilotClient

async def main():
    client = CopilotClient({"cli_path": "copilot-acp-proxy"})
    await client.start()

    session = await client.create_session({"model": "sonnet"})

    def on_event(event):
        event_type = event.type.value if hasattr(event.type, 'value') else str(event.type)
        if event_type == "assistant.message_delta":
            delta = getattr(event.data, 'deltaContent', None)
            if delta:
                print(delta, end="", flush=True)

    session.on(on_event)
    await session.send({"prompt": "Hello!"})

asyncio.run(main())
```

### Supported Backends

| Backend | Command | Model Examples |
|---------|---------|---------------|
| Gemini | `gemini` | gemini-2.0-flash, gemini-2.5-flash |
| Claude | `claude-code-acp` | opus, sonnet |
| Copilot | `copilot` | gpt-4, gpt-4o |

Environment variables:
- `ACP_PROXY_BACKEND` - Default backend (default: gemini)
- `ACP_PROXY_LOG_LEVEL` - Log level (none/error/warning/info/debug/all)
- `ACP_PROXY_LOG_FILE` - Log file path

---

## Gemini ACP Usage

**Note:** Gemini takes ~12 seconds to initialize on first connection.

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

    async with client:
        response = await client.prompt("Hello!")
        print(f"\nResponse: {response}")

asyncio.run(main())
```

### Gemini with MCP Servers

Gemini requires MCP servers to be **pre-configured** via CLI:

```bash
# Add MCP server to Gemini config
gemini mcp add nanobanana "uvx nanobanana"

# Verify
gemini mcp list
```

Then enable via `--allowed-mcp-server-names`:

```python
client = AcpClient(
    command="gemini",
    args=["--experimental-acp", "--allowed-mcp-server-names", "nanobanana"],
    cwd="/tmp",
)
```

### MCP Configuration Comparison

| Agent | Dynamic MCP (via ACP) | Pre-configured MCP |
|-------|----------------------|-------------------|
| claude-code-acp | Supported | Supported |
| Gemini CLI | Not supported | Use `--allowed-mcp-server-names` |

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

```
                    ┌─────────────────────────────────────────┐
                    │        Editors / ACP Clients            │
                    │     (Zed, Neovim, JetBrains, etc.)      │
                    └──────────────┬──────────────────────────┘
                                   │ ACP (stdio)
                                   ▼
┌──────────────────────────────────────────────────────────────┐
│                    claude-code-acp                            │
│                                                              │
│  ┌────────────────┐  ┌─────────────┐  ┌───────────────────┐ │
│  │ ClaudeAcpAgent │  │ ClaudeClient│  │    AcpClient      │ │
│  │  (ACP Server)  │  │ (Python API)│  │  (ACP Client)     │ │
│  └───────┬────────┘  └──────┬──────┘  └─────┬─────────────┘ │
│          │                  │               │               │
│          ▼                  ▼               ▼               │
│     Claude CLI         Claude CLI     Any ACP Agent         │
│    (Agent SDK)        (Agent SDK)    ┌──────────────┐       │
│                                      │ claude-code  │       │
│  ┌─────────────────────────────┐     │ gemini       │       │
│  │    AcpProxyServer           │     │ custom agent │       │
│  │  (copilot-acp-proxy)       │     └──────────────┘       │
│  │  Copilot SDK → ACP backend │                             │
│  └─────────────────────────────┘                             │
└──────────────────────────────────────────────────────────────┘
```

### Component Summary

| Component | Role | ACP? | Connects to |
|-----------|------|------|-------------|
| `ClaudeAcpAgent` | Server | Yes (Server) | Editors connect **to** it |
| `ClaudeClient` | Python API | No | Claude CLI directly |
| `AcpClient` | Client | Yes (Client) | Any ACP agent |
| `AcpProxyServer` | Proxy | Translates | Copilot SDK <-> ACP backends |

---

## What We Built

This project integrates two official Anthropic SDKs:

| Component | Source | Purpose |
|-----------|--------|---------|
| [Agent Client Protocol SDK](https://github.com/anthropics/agent-client-protocol) | Anthropic | ACP server/client protocol |
| [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python) | Anthropic | Claude CLI wrapper with streaming |

### Our Contributions

1. **ClaudeAcpAgent** (`agent.py`) - ACP server bridging Claude Agent SDK with ACP protocol. Handles bidirectional permissions, session management, streaming, MCP servers, model/command enumeration.

2. **ClaudeClient** (`client.py`) - Event-driven Python API with decorator handlers, streaming text deduplication, and simple async/await interface.

3. **AcpClient** (`acp_client.py`) - Full ACP client implementation that can connect to any ACP-compatible agent via subprocess. Includes file/terminal operation interception.

4. **AcpProxyServer** (`proxy/`) - Copilot SDK compatibility layer. Translates Copilot SDK JSON-RPC protocol to ACP, enabling Copilot SDK apps to use Claude, Gemini, or other backends.

### Why This Package?

| Approach | API Key | Subscription | ACP Support | Multi-Agent | Event-Driven |
|----------|---------|--------------|-------------|-------------|--------------|
| Anthropic API directly | Required | No | No | No | No |
| Claude Agent SDK | No | Uses CLI | No | No | Partial |
| **claude-code-acp** | No | Uses CLI | Full | Yes | Full |

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

### Auto-approve Mode

```python
import asyncio
from claude_code_acp import ClaudeClient

async def main():
    client = ClaudeClient(cwd=".")
    await client.set_mode("bypassPermissions")

    @client.on_text
    async def on_text(text):
        print(text, end="")

    await client.query("Create a complete Flask app with tests")

asyncio.run(main())
```

### Multi-Agent Comparison

```python
import asyncio
from claude_code_acp import AcpClient

async def ask(agent_name, command, args, prompt):
    client = AcpClient(command=command, args=args)

    @client.on_text
    async def on_text(text):
        pass  # collect silently

    async with client:
        response = await client.prompt(prompt)
        print(f"{agent_name}: {response[:100]}...")

async def main():
    await asyncio.gather(
        ask("Claude", "claude-code-acp", [], "What is ACP?"),
        ask("Gemini", "gemini", ["--experimental-acp"], "What is ACP?"),
    )

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

# Run ACP server locally
uv run claude-code-acp

# Run Copilot proxy locally
uv run copilot-acp-proxy --backend gemini

# Run tests
uv run pytest tests/test_unit_*.py -v        # Unit tests (fast)
uv run pytest tests/ -m integration -v        # Integration tests (need Claude CLI)
```

---

## Related Projects

- [claude-code-acp](https://github.com/zed-industries/claude-code-acp) - TypeScript version by Zed Industries
- [agent-client-protocol](https://github.com/anthropics/agent-client-protocol) - ACP specification and SDKs
- [claude-agent-sdk-python](https://github.com/anthropics/claude-agent-sdk-python) - Official Claude Agent SDK

---

## License

MIT
