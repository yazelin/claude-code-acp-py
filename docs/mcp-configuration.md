# MCP 配置指南

## 概述

MCP (Model Context Protocol) 允許 AI agents 使用外部工具和服務。不同的 ACP Server 對 MCP 的支援方式不同。

## 支援比較

| ACP Server | 動態 MCP | 預配置 MCP | 配置方式 |
|------------|----------|-----------|---------|
| claude-code-acp | ✅ | ✅ | `mcp_servers` 參數 |
| Gemini CLI | ❌ | ✅ | `gemini mcp add` + CLI flag |
| Copilot | 🔄 | 🔄 | 待測試 |

## claude-code-acp 的 MCP 配置

### 動態配置 (推薦)

通過 `mcp_servers` 參數傳入：

```python
from claude_code_acp import AcpClient

client = AcpClient(
    command="claude-code-acp",
    cwd="/tmp",
    mcp_servers=[
        {
            "name": "nanobanana",
            "command": "uvx",
            "args": ["nanobanana-py"],  # 注意: package name 是 nanobanana-py
            "env": {"NANOBANANA_GEMINI_API_KEY": "your-key"},  # 或 GEMINI_API_KEY
        },
    ],
)
```

### 配置格式

```python
mcp_servers = [
    {
        "name": str,      # MCP server 識別名稱
        "command": str,   # 執行的命令
        "args": list,     # 命令參數列表
        "env": dict,      # 環境變數 (可選)
    },
]
```

### 常見 MCP Server 配置

#### nanobanana-py (圖片生成)

```python
{
    "name": "nanobanana",
    "command": "uvx",
    "args": ["nanobanana-py"],  # Package name 是 nanobanana-py
    "env": {
        # 環境變數優先順序: NANOBANANA_GEMINI_API_KEY > GEMINI_API_KEY
        "NANOBANANA_GEMINI_API_KEY": "your-gemini-api-key",
    },
}
```

#### filesystem (檔案系統)

```python
{
    "name": "filesystem",
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/allowed/path"],
    "env": {},
}
```

#### fetch (HTTP 請求)

```python
{
    "name": "fetch",
    "command": "uvx",
    "args": ["mcp-server-fetch"],
    "env": {},
}
```

## Gemini CLI 的 MCP 配置

### Step 1: 預先配置 MCP Server

```bash
# 新增 MCP server
gemini mcp add <name> <command> [args...]

# 範例 (注意: package name 是 nanobanana-py)
gemini mcp add nanobanana "uvx nanobanana-py"

# 如果需要環境變數，使用 bash wrapper
gemini mcp add nanobanana "bash -c 'source /path/to/.env && uvx nanobanana-py'"
# 或
gemini mcp add nanobanana "bash -c 'export NANOBANANA_GEMINI_API_KEY=xxx && uvx nanobanana-py'"

# 查看已配置的 servers
gemini mcp list

# 移除 server
gemini mcp remove nanobanana
```

### Step 2: 啟動時啟用 MCP

```python
client = AcpClient(
    command="gemini",
    args=[
        "--experimental-acp",
        "--allowed-mcp-server-names", "nanobanana",
    ],
)
```

### 多個 MCP Servers

```bash
# 配置多個
gemini mcp add nanobanana "bash -c 'source ~/.env && uvx nanobanana-py'"
gemini mcp add filesystem "npx -y @modelcontextprotocol/server-filesystem /tmp"
```

```python
# 啟用多個
client = AcpClient(
    command="gemini",
    args=[
        "--experimental-acp",
        "--allowed-mcp-server-names", "nanobanana",
        "--allowed-mcp-server-names", "filesystem",
    ],
)
```

## 為什麼 Gemini 不支援動態 MCP？

Gemini CLI 的 ACP 實現不接受通過 `session/new` 請求傳入的 MCP 配置。這可能是出於安全考量或實現限制。

**解決方案**: 使用預配置 + CLI flag 的方式。

## 環境變數處理

### claude-code-acp

直接在 `env` 欄位傳入：

```python
mcp_servers=[{
    "env": {
        "API_KEY": "secret",
        "DEBUG": "true",
    },
}]
```

### Gemini CLI

使用 bash wrapper：

```bash
gemini mcp add myserver "bash -c 'source /path/to/.env && uvx myserver'"
```

或內嵌環境變數：

```bash
gemini mcp add myserver "bash -c 'export API_KEY=secret && uvx myserver'"
```

## 除錯技巧

### 確認 MCP 已載入

詢問 agent 有哪些工具：

```python
response = await client.prompt("What tools do you have available?")
```

### 檢查 MCP Server 狀態 (Gemini)

```bash
gemini mcp list
# 應該顯示 "Connected" 狀態
```

### 常見問題

1. **MCP 工具沒出現**: 檢查配置和啟用 flag
2. **連接失敗**: 確認 MCP server 命令可執行
3. **權限錯誤**: 檢查環境變數是否正確傳入
