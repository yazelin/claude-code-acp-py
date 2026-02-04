# claude-code-acp 使用指南

## 概述

`claude-code-acp` 是本套件提供的 ACP Server，基於 Claude Agent SDK 實現。

**狀態**: ✅ 完整支援

## 安裝

```bash
pip install claude-code-acp

# 或使用 uv
uv tool install claude-code-acp
```

## 前置需求

需要先安裝並登入 Claude CLI：

```bash
# 安裝 Claude CLI (依照 Anthropic 官方指南)
# 然後登入
claude /login
```

## 作為 ACP Server 使用

### 啟動 Server

```bash
claude-code-acp
```

### Zed Editor 配置

在 `~/.config/zed/settings.json` 加入：

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

### Neovim 配置

參考 ACP 官方文件配置你的 Neovim ACP client。

## 作為 ACP Client 連接

```python
import asyncio
from claude_code_acp import AcpClient

async def main():
    client = AcpClient(
        command="claude-code-acp",
        cwd="/your/project",
    )

    @client.on_text
    async def on_text(text):
        print(text, end="", flush=True)

    @client.on_tool_start
    async def on_tool_start(tool_id, name, input_data):
        print(f"\n🔧 {name}")

    @client.on_permission
    async def on_permission(name, input_data, options):
        print(f"🔐 需要權限: {name}")
        return "allow"  # 或 "reject", "allow_always"

    async with client:
        response = await client.prompt("列出當前目錄的檔案")
        print(f"\n回應: {response}")

asyncio.run(main())
```

## MCP 配置

### ✅ 支援動態 MCP 配置

`claude-code-acp` 支援通過 `mcp_servers` 參數動態傳入 MCP server 配置：

```python
client = AcpClient(
    command="claude-code-acp",
    cwd="/tmp",
    mcp_servers=[
        {
            "name": "nanobanana",
            "command": "uvx",
            "args": ["nanobanana-py"],  # 注意：package name 是 nanobanana-py
            "env": {
                "NANOBANANA_GEMINI_API_KEY": "your-api-key",  # 或 GEMINI_API_KEY
            },
        },
        {
            "name": "another-mcp",
            "command": "npx",
            "args": ["-y", "@some/mcp-server"],
            "env": {},
        },
    ],
)
```

### MCP 配置格式

```python
mcp_servers = [
    {
        "name": str,      # MCP server 名稱 (必填)
        "command": str,   # 執行命令 (必填)
        "args": list,     # 命令參數 (選填, 預設 [])
        "env": dict,      # 環境變數 (選填, 預設 {})
    },
]
```

### 完整 MCP 範例

```python
import asyncio
import os
from claude_code_acp import AcpClient

async def main():
    # 取得 API key (優先順序: NANOBANANA_GEMINI_API_KEY > GEMINI_API_KEY)
    api_key = os.environ.get("NANOBANANA_GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY", "")

    client = AcpClient(
        command="claude-code-acp",
        cwd="/tmp",
        mcp_servers=[{
            "name": "nanobanana",
            "command": "uvx",
            "args": ["nanobanana-py"],  # 正確的 package name
            "env": {
                "NANOBANANA_GEMINI_API_KEY": api_key,
            },
        }],
    )

    @client.on_text
    async def on_text(text):
        print(text, end="", flush=True)

    @client.on_tool_start
    async def on_tool_start(tool_id, name, input_data):
        print(f"\n🔧 使用工具: {name}")

    @client.on_permission
    async def on_permission(name, input_data, options):
        return "allow"

    async with client:
        response = await client.prompt(
            "使用 nanobanana 生成一張紅色圓形圖片，儲存到 /tmp/circle.png"
        )
        print(f"\n回應: {response}")

    # 檢查結果
    if os.path.exists("/tmp/circle.png"):
        print(f"✅ 圖片已生成: /tmp/circle.png")

asyncio.run(main())
```

## 權限模式

支援四種權限模式：

```python
# 預設模式 - 需要確認每個操作
await client.set_mode("default")

# 接受編輯模式 - 自動接受檔案編輯
await client.set_mode("acceptEdits")

# 計畫模式 - 只規劃不執行
await client.set_mode("plan")

# 繞過權限模式 - 自動接受所有操作 (謹慎使用)
await client.set_mode("bypassPermissions")
```

## 事件處理器

| 事件 | 參數 | 說明 |
|------|------|------|
| `@client.on_text` | `(text: str)` | 收到文字回應 |
| `@client.on_thinking` | `(text: str)` | 收到思考過程 |
| `@client.on_tool_start` | `(tool_id, name, input)` | 工具開始執行 |
| `@client.on_tool_end` | `(tool_id, status, output)` | 工具執行完成 |
| `@client.on_permission` | `(name, input, options) -> str` | 需要權限確認 |
| `@client.on_error` | `(exception)` | 發生錯誤 |
| `@client.on_complete` | `()` | 完成 |

## 與其他 Server 的比較

| 特性 | claude-code-acp | Gemini | Copilot |
|------|-----------------|--------|---------|
| 初始化時間 | ~1-2 秒 | ~12 秒 | 待測試 |
| 動態 MCP | ✅ | ❌ | 待測試 |
| 權限控制 | ✅ 完整 | ✅ 基本 | 待測試 |
| Thinking events | ✅ | ✅ | 待測試 |
| 認證 | Claude CLI | Google | GitHub |

## 常見問題

### Q: 出現 "Claude CLI not found" 錯誤？

確保 Claude CLI 已安裝並在 PATH 中：

```bash
which claude
claude /login
```

### Q: MCP server 沒有載入？

檢查：
1. MCP 配置格式是否正確
2. 命令是否可執行 (`uvx`, `npx` 等)
3. 環境變數是否設定正確
4. Package name 是否正確 (例如 `nanobanana-py` 而非 `nanobanana`)

### Q: nanobanana MCP 沒有 API key？

nanobanana-py 支援多種環境變數名稱 (優先順序):
1. `NANOBANANA_GEMINI_API_KEY` (建議)
2. `NANOBANANA_GOOGLE_API_KEY`
3. `GEMINI_API_KEY` (備援)
4. `GOOGLE_API_KEY` (備援)

### Q: 權限請求沒有觸發 on_permission？

確保沒有使用 `bypassPermissions` 模式：

```python
await client.set_mode("default")  # 使用預設模式
```

## 測試結果

| 功能 | 狀態 |
|------|------|
| 基本 prompt | ✅ |
| Text streaming | ✅ |
| Thinking events | ✅ |
| Tool calls | ✅ |
| Permission requests | ✅ |
| 動態 MCP | ✅ |
| Session management | ✅ |
