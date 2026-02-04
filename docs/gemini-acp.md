# Gemini CLI ACP 使用指南

## 概述

Gemini CLI 支援 ACP (Agent Client Protocol) 模式，可以通過 `AcpClient` 連接使用。

**狀態**: ✅ 測試通過

## 安裝

```bash
# 安裝 Gemini CLI
npm install -g @anthropics/gemini-cli

# 或使用 npx
npx @anthropics/gemini-cli
```

## 基本用法

```python
import asyncio
from claude_code_acp import AcpClient

async def main():
    client = AcpClient(
        command="gemini",
        args=["--experimental-acp"],
        cwd="/your/working/directory",
    )

    @client.on_text
    async def on_text(text):
        print(text, end="", flush=True)

    @client.on_thinking
    async def on_thinking(text):
        print(f"[思考] {text[:60]}...")

    @client.on_complete
    async def on_complete():
        print("\n--- 完成 ---")

    async with client:
        response = await client.prompt("Hello, Gemini!")
        print(f"\n回應: {response}")

asyncio.run(main())
```

## ⚠️ 重要注意事項

### 1. 初始化時間長 (~12 秒)

Gemini ACP 首次連接需要約 **12 秒** 進行初始化：

```python
# connect() 會花費 ~12 秒
async with client:  # <-- 這裡等待 ~12 秒
    # 之後的操作會比較快
    response = await client.prompt("Hi")  # <-- ~2-5 秒
```

**建議**:
- 不要設太短的 timeout
- 可以顯示 "正在連接..." 提示用戶

### 2. `initialize()` 和 `new_session()` 時間分配

| 呼叫順序 | 有 initialize() | 無 initialize() |
|---------|----------------|-----------------|
| initialize() | ~12 秒 | - |
| new_session() | ~1 秒 | ~12 秒 |
| prompt() | ~2-5 秒 | ~2-5 秒 |

**說明**: 無論是否呼叫 `initialize()`，第一個請求都會花費 ~12 秒。

### 3. 斷開連接可能超時

Gemini 不會優雅地關閉，`disconnect()` 可能會超時：

```
Process terminate timed out, killing
```

這是正常的，我們的 `AcpClient` 已經處理了這個情況（加入 timeout）。

## MCP 配置

### Gemini 不支援動態 MCP 配置

❌ **不支援** 通過 ACP protocol 的 `session/new` 傳入 MCP：

```python
# ❌ 這樣不會生效
client = AcpClient(
    command="gemini",
    args=["--experimental-acp"],
    mcp_servers=[{"name": "my-mcp", ...}],  # Gemini 會忽略這個
)
```

### 正確的 MCP 配置方式

**Step 1**: 用 Gemini CLI 預先配置 MCP server

```bash
# 新增 MCP server
gemini mcp add nanobanana "uvx nanobanana"

# 如果需要環境變數
gemini mcp add nanobanana "bash -c 'source /path/to/.env && uvx nanobanana'"

# 查看已配置的 servers
gemini mcp list

# 移除 server
gemini mcp remove nanobanana
```

**Step 2**: 啟動時指定允許的 MCP server

```python
client = AcpClient(
    command="gemini",
    args=[
        "--experimental-acp",
        "--allowed-mcp-server-names", "nanobanana",  # ✅ 啟用預配置的 MCP
    ],
)
```

**Step 3**: 使用 MCP tools

```python
async with client:
    # Gemini 現在可以使用 nanobanana 的 tools
    response = await client.prompt("用 nanobanana 生成一張紅色圓形圖片")
```

### 完整 MCP 範例

```python
import asyncio
from claude_code_acp import AcpClient

async def main():
    # 假設已經執行: gemini mcp add nanobanana "uvx nanobanana"

    client = AcpClient(
        command="gemini",
        args=[
            "--experimental-acp",
            "--allowed-mcp-server-names", "nanobanana",
        ],
        cwd="/tmp",
    )

    @client.on_text
    async def on_text(text):
        print(text, end="", flush=True)

    @client.on_tool_start
    async def on_tool_start(tool_id, name, input_data):
        print(f"\n🔧 使用工具: {name}")

    async with client:
        print("連接中 (約 12 秒)...")
        response = await client.prompt(
            "使用 nanobanana 生成一張簡單的藍色方塊圖片，儲存到 /tmp/blue_square.png"
        )
        print(f"\n回應: {response}")

asyncio.run(main())
```

## CLI 參數參考

| 參數 | 說明 |
|------|------|
| `--experimental-acp` | 啟用 ACP 模式 (必須) |
| `--allowed-mcp-server-names <name>` | 允許使用的 MCP server 名稱 |
| `--debug` | 開啟除錯模式 |

## 常見問題

### Q: 為什麼連接這麼慢？

Gemini CLI 在 ACP 模式下需要初始化，這個過程約 12 秒。這是 Gemini 的設計，不是 bug。

### Q: MCP tools 沒有出現？

確認：
1. 已用 `gemini mcp add` 配置
2. 啟動時有加 `--allowed-mcp-server-names`
3. 用 `gemini mcp list` 確認 server 狀態是 "Connected"

### Q: 斷開連接時出現錯誤訊息？

```
Process terminate timed out, killing
RuntimeError: Event loop is closed
```

這些是正常的清理訊息，不影響功能。

## 測試結果

| 功能 | 狀態 | 備註 |
|------|------|------|
| 基本 prompt | ✅ | 正常 |
| Thinking events | ✅ | 正常 |
| Text streaming | ✅ | 正常 |
| MCP (預配置) | ✅ | 需用 CLI 配置 |
| MCP (動態) | ❌ | 不支援 |
| Tool calls | ✅ | 正常 |
