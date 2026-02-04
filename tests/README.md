# 測試記錄

## 測試環境

```
Platform: Linux
Platform Version: #37~24.04.1-Ubuntu SMP
Python: 3.11.13
claude-code-acp: v0.3.6
Gemini CLI: 0.26.0
GitHub Copilot CLI: 0.0.402
Copilot SDK (Python): 0.1.21
測試日期: 2025-02-05
```

## 測試結果總覽

| 測試項目 | 狀態 | 說明 |
|---------|------|------|
| [AcpClient → claude-code-acp](./test_acp_client_claude.py) | ✅ PASS | 基本功能 + Tool use |
| [AcpClient → claude-code-acp + MCP](./test_acp_client_claude_mcp.py) | ✅ PASS | 動態 MCP 配置 |
| [AcpClient → Gemini ACP](./test_acp_client_gemini.py) | ✅ PASS | 基本功能 |
| [AcpClient → Gemini + MCP](./test_acp_client_gemini_mcp.py) | ✅ PASS | 需預配置 MCP |
| [AcpClient → Copilot ACP](./test_acp_client_copilot.py) | ✅ PASS | 基本功能 + Tool use |
| [AcpClient → Copilot ACP + MCP](./test_acp_client_copilot_mcp.py) | ✅ PASS | 動態 MCP 配置 |
| [Copilot SDK → claude-code-acp](./test_copilot_sdk_claude_server.py) | ❌ FAIL | 協議不相容 |
| Copilot SDK → Gemini ACP | ❌ FAIL | 協議不相容 |
| [Copilot SDK + BYOK → Gemini API](./test_copilot_sdk_byok_gemini.py) | ✅ PASS | HTTP API (非 ACP) |
| [Copilot SDK + BYOK → Anthropic API](./test_copilot_sdk_byok_anthropic.py) | 🔄 待測試 | 需 ANTHROPIC_API_KEY |

## 執行測試

```bash
# 測試 AcpClient → claude-code-acp
python tests/test_acp_client_claude.py

# 測試 AcpClient → Gemini
python tests/test_acp_client_gemini.py

# 測試 AcpClient → Gemini + MCP (需先配置)
# gemini mcp add nanobanana "uvx nanobanana"
python tests/test_acp_client_gemini_mcp.py
```

## 詳細測試結果

### AcpClient → claude-code-acp

**測試日期**: 2025-02-04

| 功能 | 結果 | 耗時 |
|------|------|------|
| 連接 | ✅ | ~1.2s |
| 簡單 prompt | ✅ | ~4.3s |
| Tool use (ls) | ✅ | ~5.4s |
| on_text event | ✅ | - |
| on_tool_start event | ✅ | - |
| on_tool_end event | ✅ | - |
| on_complete event | ✅ | - |
| on_permission event | ✅ | - |

### AcpClient → Gemini ACP

**測試日期**: 2025-02-04

| 功能 | 結果 | 耗時 |
|------|------|------|
| 連接 (含初始化) | ✅ | ~12s |
| 簡單 prompt | ✅ | ~5s |
| on_text event | ✅ | - |
| on_thinking event | ✅ | - |
| on_complete event | ✅ | - |

**注意**: Gemini 初始化需要約 12 秒

### AcpClient → Gemini + MCP

**測試日期**: 2025-02-04

**前置條件**:
```bash
gemini mcp add nanobanana "uvx nanobanana-py"
```

| 功能 | 結果 | 說明 |
|------|------|------|
| MCP 動態配置 | ❌ | Gemini 不支援 |
| MCP 預配置 + flag | ✅ | 使用 --allowed-mcp-server-names |
| MCP tools 可用 | ✅ | 顯示 nanobanana tools |

### AcpClient → Copilot ACP

**測試日期**: 2025-02-05

| 功能 | 結果 | 耗時 |
|------|------|------|
| 連接 | ✅ | ~4.9s |
| 簡單 prompt | ✅ | ~17.3s |
| Tool use (ls) | ✅ | ~35.0s |
| on_text event | ✅ | - |
| on_tool_start event | ✅ | - |
| on_permission event | ✅ | - |

**執行方式**:
```bash
python tests/test_acp_client_copilot.py
```

### AcpClient → Copilot ACP + MCP

**測試日期**: 2025-02-05

| 功能 | 結果 | 耗時 |
|------|------|------|
| 連接 (含 MCP 初始化) | ✅ | ~6.3s |
| MCP tools 可用 | ✅ | - |

**Copilot MCP 配置格式** (與 Claude/Gemini 不同):
```json
{
  "mcpServers": {
    "nanobanana": {
      "type": "local",
      "command": "uvx",
      "args": ["nanobanana-py"],
      "tools": ["*"],
      "env": {
        "NANOBANANA_GEMINI_API_KEY": "${NANOBANANA_GEMINI_API_KEY}"
      }
    }
  }
}
```

**重要差異**:
- 需要 `"type": "local"` (不是 `"stdio"`)
- 需要 `"tools": ["*"]` 欄位
- 環境變數使用 `${VAR}` 語法

**配置方式**:
1. 專案配置: `.copilot/mcp-config.json`
2. 全域配置: `~/.copilot/mcp-config.json`
3. 臨時配置: `--additional-mcp-config "@/path/to/config.json"`

### Copilot SDK → 其他 CLI (不相容)

**測試日期**: 2025-02-05

**測試 SDK**:
- Python: `github-copilot-sdk` (v0.1.21)
- Node.js: `@github/copilot-sdk` (v0.1.21)

| 目標 CLI | 結果 | 原因 |
|---------|------|------|
| claude-code-acp | ❌ TIMEOUT | CLI flags 不相容 |
| Gemini CLI | ❌ FAIL | CLI flags 不相容 |

**錯誤訊息**:
```
Unknown arguments: headless, log-level, logLevel, stdio
```

**原因分析**:
Copilot SDK 在啟動 CLI 時會自動傳送以下 flags:
```
--headless --server --log-level debug --stdio
```

這些 flags 只有 Copilot CLI 認識，其他 CLI (Gemini、claude-code-acp) 不支援。

## 已知限制

1. **Gemini 初始化慢**: ~12 秒
2. **Gemini 不支援動態 MCP**: 需用 CLI 預配置
3. **Copilot 初始化較慢**: 第一次 prompt ~17s
4. **Copilot SDK 只能連 Copilot CLI**: SDK 傳送的 CLI flags 其他 CLI 不認識
5. **斷開連接警告**: 正常現象，不影響功能

## MCP 配置格式對照

| CLI | 動態 MCP | 配置格式 | type 欄位 | 額外欄位 |
|-----|---------|---------|----------|---------|
| claude-code-acp | ✅ | JSON array | 不需要 | - |
| Gemini | ❌ | CLI 預配置 | - | - |
| Copilot | ✅ | JSON object | `"local"` | `"tools": ["*"]` |

---

## Copilot SDK BYOK (Bring Your Own Key)

### 什麼是 BYOK?

BYOK 讓你用自己的 API Key 連接不同的模型提供商，繞過 GitHub Copilot 認證。

### 架構差異

```
方式 1: Copilot SDK → 其他 CLI (❌ 不支援)
┌─────────────┐     ???        ┌──────────────┐
│ Copilot SDK │ ─────────────▶ │ Gemini CLI   │  ← CLI flags 不相容
└─────────────┘                │ claude-code  │
                               └──────────────┘

方式 2: Copilot SDK + BYOK → HTTP API (✅ 支援)
┌─────────────┐   ACP/stdio    ┌─────────────┐   HTTP API   ┌──────────────┐
│ Copilot SDK │ ─────────────▶ │ Copilot CLI │ ───────────▶ │ Provider API │
└─────────────┘                └─────────────┘              └──────────────┘
                                                            (Gemini, Anthropic,
                                                             OpenAI, Ollama)
```

### 支援的 Provider

| Provider | type 值 | 說明 |
|----------|---------|------|
| OpenAI | `"openai"` | OpenAI API 和相容端點 |
| Azure OpenAI | `"azure"` | Azure 託管模型 |
| Anthropic | `"anthropic"` | Claude 模型 |
| Gemini | `"openai"` | Google Gemini API (OpenAI 相容模式) |
| Ollama | `"openai"` | 本地模型 |

### Copilot SDK + BYOK → Gemini API

**測試日期**: 2025-02-05

| 功能 | 結果 | 耗時 |
|------|------|------|
| 連接 | ✅ | ~2.9s |
| BYOK Gemini API | ✅ | ~2.5s |

**程式碼範例**:
```python
from copilot import CopilotClient
import os

client = CopilotClient()
await client.start()

session = await client.create_session({
    "model": "gemini-2.0-flash",
    "provider": {
        "type": "openai",  # Gemini API 支援 OpenAI 相容模式
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "api_key": os.environ["GEMINI_API_KEY"],
    },
})
```

### Copilot SDK + BYOK → Anthropic API

**程式碼範例**:
```python
from copilot import CopilotClient
import os

client = CopilotClient()
await client.start()

session = await client.create_session({
    "model": "claude-sonnet-4-20250514",
    "provider": {
        "type": "anthropic",
        "base_url": "https://api.anthropic.com",
        "api_key": os.environ["ANTHROPIC_API_KEY"],
    },
})
```

### 重要結論

1. **Copilot SDK 不能連接其他 CLI 的 ACP server** (CLI flags 不相容)
2. **但可以透過 BYOK 連接各種 HTTP API** (Gemini API, Anthropic API 等)
3. **BYOK 仍需要 Copilot CLI** 作為中間層
4. **這是 HTTP API 呼叫，不是 ACP 連接**

### 參考資料

- [Copilot SDK BYOK 文件](https://github.com/github/copilot-sdk/blob/main/docs/auth/byok.md)
- [Copilot SDK Cookbook](https://github.com/github/awesome-copilot/tree/main/cookbook/copilot-sdk)

---

## 重要結論：Copilot SDK 不是通用 ACP Client

### 比較表

| 特性 | Copilot SDK | AcpClient (我們的) |
|------|-------------|-------------------|
| 連接 Copilot CLI (`copilot --acp`) | ✅ | ✅ |
| 連接 Gemini CLI (`gemini --experimental-acp`) | ❌ | ✅ |
| 連接 claude-code-acp | ❌ | ✅ |
| 通用 ACP Client | ❌ | ✅ |

### 原因

Copilot SDK 啟動 CLI 時會自動傳送特定的 flags：
```
--headless --server --log-level debug --stdio
```

這些 flags 只有 Copilot CLI 認識，其他 CLI 會報錯：
```
Unknown arguments: headless, log-level, logLevel, stdio
```

### 結論

```
Copilot SDK = 專為 Copilot CLI 設計的專用 SDK
AcpClient   = 通用 ACP Client (可連接任何 ACP Server)
```

Copilot SDK 雖然底層使用 JSON-RPC，但它不是一個通用的 ACP client。如果需要連接不同的 ACP server (Gemini、Claude 等)，應該使用通用的 ACP client 實作。
