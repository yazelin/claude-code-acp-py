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
| **[Copilot SDK → ACP Proxy → Gemini](./test_copilot_sdk_via_proxy.py)** | ✅ PASS | **突破！透過 Proxy 連接** |
| **[Copilot SDK → ACP Proxy → claude-code-acp](./test_copilot_sdk_via_proxy_claude.py)** | ✅ PASS | **Proxy 連接 Claude** |
| **[Copilot SDK → ACP Proxy → Copilot CLI](./test_copilot_sdk_via_proxy_copilot.py)** | ✅ PASS | **架構完整性驗證** |

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

### Node.js SDK 的 cliPath 參數無效

**測試日期**: 2025-02-05

測試 Node.js `@github/copilot-sdk` 的 `cliPath` 參數：

```javascript
// 嘗試指定使用 Gemini CLI
const session = await client.createSession({
  model: "gemini-2.0-flash",
  cliPath: "gemini",
  cliArgs: "--experimental-acp"
});
```

**測試結果**（問模型 "What is your model name?"）：

| 設定 | 回應 |
|------|------|
| 預設 `{}` | GPT-4 |
| `model: "gemini-2.0-flash"` | GPT-4 |
| `cliPath: "gemini"` | GPT-4 |
| `cliPath: "claude-code-acp"` | GPT-4 |

**結論**: `cliPath` 和 `model` 參數都被忽略！SDK 始終連接到 Copilot CLI (GPT-4)。

即使 `copilot-sdk-demo` 範例寫了 `cliPath: "gemini"`，實際上還是使用 Copilot CLI。

### 結論

```
Copilot SDK = 專為 Copilot CLI 設計的專用 SDK
AcpClient   = 通用 ACP Client (可連接任何 ACP Server)
```

Copilot SDK 雖然底層使用 JSON-RPC，但它不是一個通用的 ACP client。

**但是**，我們實作了 **ACP Proxy** 來解決這個問題！

---

## 🎉 突破：ACP Proxy

### 什麼是 ACP Proxy?

我們實作的 `copilot-acp-proxy` 可以讓 Copilot SDK 連接到任何 ACP backend！

### 架構

```
┌─────────────┐   Copilot Protocol   ┌─────────────────┐   Standard ACP   ┌─────────────┐
│ Copilot SDK │ ──────────────────── │ copilot-acp-    │ ──────────────── │ Backend CLI │
│             │   (JSON-RPC 2.0)     │ proxy           │  (JSON-RPC 2.0)  │ gemini/     │
│             │   Content-Length     │                 │                   │ claude-code │
└─────────────┘                      └─────────────────┘                   └─────────────┘
```

### 測試結果

**測試日期**: 2025-02-05

| 測試項目 | 結果 | 耗時 |
|---------|------|------|
| Copilot SDK → Proxy 連接 | ✅ | ~1.3s |
| Proxy → Gemini CLI 連接 | ✅ | - |
| 簡單 Prompt | ✅ | ~6.3s |

**回應內容**: "Hello from Gemini via Proxy!"

### 使用方式

```python
import os
from copilot import CopilotClient

# 設定後端 (gemini, claude-code-acp, etc.)
os.environ["ACP_PROXY_BACKEND"] = "gemini"

# 使用 Copilot SDK
client = CopilotClient({"cli_path": "copilot-acp-proxy"})
await client.start()

session = await client.create_session({"model": "gemini-2.0-flash"})
session.on(lambda event: print(event.type, event.data))
await session.send({"prompt": "Hello!"})
```

### 技術細節

1. **協議版本**: Protocol Version 2 (配合 Copilot SDK 0.1.x)
2. **訊息格式**: LSP-style Content-Length headers
3. **Event 欄位**: `id` (UUID), `type`, `timestamp` (ISO 8601), `data`

### 支援的後端

| Backend | 環境變數設定 | 狀態 | 耗時 |
|---------|-------------|------|------|
| Gemini CLI | `ACP_PROXY_BACKEND=gemini` | ✅ 已測試 | ~6.3s |
| claude-code-acp | `ACP_PROXY_BACKEND=claude-code-acp` | ✅ 已測試 | ~6.4s |
| Copilot CLI | `ACP_PROXY_BACKEND=copilot` | ✅ 已測試 | ~12.8s |

### ACP Proxy 完整測試結果

**測試日期**: 2025-02-05

| 測試項目 | Backend | 連接時間 | Prompt 時間 | 結果 |
|---------|---------|---------|-------------|------|
| [test_copilot_sdk_via_proxy.py](./test_copilot_sdk_via_proxy.py) | Gemini | 1.3s | 6.3s | ✅ PASS |
| [test_copilot_sdk_via_proxy_claude.py](./test_copilot_sdk_via_proxy_claude.py) | claude-code-acp | 1.5s | 6.4s | ✅ PASS |
| [test_copilot_sdk_via_proxy_copilot.py](./test_copilot_sdk_via_proxy_copilot.py) | Copilot CLI | 2.2s | 12.8s | ✅ PASS |

### Tool Use 測試結果

**測試日期**: 2025-02-05

透過 ACP Proxy 測試各後端的 Tool Use 功能：

| Backend | Tool Use | 時間 | 結果 | 備註 |
|---------|----------|------|------|------|
| claude-code-acp | ✅ 成功 | ~6s | 執行 `ls` 成功 | 穩定快速 |
| Gemini | ⚠️ 部分成功 | ~82s | `ls` 失敗，fallback 到 `list_directory` | 非常慢 |
| Copilot | - | - | 未詳細測試 | - |

#### Gemini Tool Use 詳細分析

直接使用 AcpClient 測試 Gemini 的 Tool Use：

```
[1] 連接 Gemini... ✅ (14.7s)
[2] 發送 prompt (要求執行 ls)...
    🤔 Thinking... (多次思考)
    🔐 Permission: ls -F -> auto approve
    ✅ Tool End: failed  ← Shell 指令失敗
    🔐 Permission: ls -F -> auto approve
    ✅ Tool End: failed  ← 再次失敗
    🔧 Tool Start: list_directory ← 自動切換工具
    ✅ Tool End: completed
    ✅ Complete! (81.7s)
```

**發現**:
1. Gemini 的 shell tool 執行 `ls` 指令會失敗
2. Gemini 會自動 fallback 到 `list_directory` 工具
3. 整個過程非常慢 (~82 秒)
4. 透過 Copilot SDK Proxy 會因 SDK 內部 timeout 而失敗

#### 模型身份測試

詢問各後端 "What language model are you?"：

| Backend | 回答 |
|---------|------|
| Gemini | "I am Gemini, a large language model built by Google." |
| Claude | "I am Claude, an AI assistant made by Anthropic..." |
| Copilot | (空回應) |

#### Model 參數修復

**修復日期**: 2025-02-05

**問題描述**:
透過 Copilot SDK 指定 `model: "opus"` 時，實際回應的是 Claude 3.5 Sonnet 而非 Opus。

**原因分析**:
1. Copilot SDK 將 `model` 參數傳給 Proxy
2. Proxy 的 `create_session` 接收 `model` 但只存儲，沒有轉發
3. `claude-code-acp` Agent 的 `set_session_model` 只是 stub，沒有實際功能
4. `ClaudeAgentOptions` 創建時沒有傳入 `model` 參數

**修復內容**:

| 檔案 | 修改 |
|------|------|
| `agent.py` | Session 新增 `model` 欄位 |
| `agent.py` | `set_session_model` 實際儲存 model |
| `agent.py` | `ClaudeAgentOptions` 傳入 `model=session.model` |
| `acp_client.py` | 新增 `set_model()` 方法 |
| `session_manager.py` | 建立 session 後呼叫 `set_model` |

**正確流程**:
```
Copilot SDK (model: "opus")
    ↓ session.create
ACP Proxy
    ↓ set_session_model("opus")
claude-code-acp Agent
    ↓ session.model = "opus"
Claude Agent SDK
    ↓ ClaudeAgentOptions(model="opus")
Claude Opus 4.5 ✅
```

**測試結果**:

| 測試 | 修復前 | 修復後 |
|------|--------|--------|
| `model: "opus"` | Claude 3.5 Sonnet | **Claude Opus 4.5** ✅ |
| 回應內容 | "我是 Claude 3.5 Sonnet..." | "I am Claude Opus 4.5 (claude-4opus-20250415)..." |

**範例程式**:
```python
# examples/copilot_sdk_via_proxy.py
os.environ["ACP_PROXY_BACKEND"] = "claude-code-acp"

client = CopilotClient({"cli_path": "copilot-acp-proxy"})
await client.start()

session = await client.create_session({"model": "opus"})  # ← 現在有效！
```

**可用 Model 參數**:

| Backend | 可用值 |
|---------|--------|
| claude-code-acp | `opus`, `sonnet`, `haiku` 或完整 ID |
| Gemini | `gemini-2.5-pro`, `gemini-2.5-flash`, etc. |
| Copilot | `gpt-4`, `gpt-4o`, etc. |
