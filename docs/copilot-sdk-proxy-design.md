# Copilot SDK → ACP Proxy 設計文件

## 目標

讓 Copilot SDK 能夠連接到任何支援 ACP 的 CLI (Gemini, claude-code-acp 等)。

## 架構

```
┌─────────────┐   Copilot Protocol   ┌─────────────┐   Standard ACP   ┌─────────────┐
│ Copilot SDK │ ──────────────────── │  ACP Proxy  │ ──────────────── │ Backend CLI │
│             │   (JSON-RPC/stdio)   │             │  (JSON-RPC/stdio) │ gemini/     │
│             │                      │             │                   │ claude-code │
└─────────────┘                      └─────────────┘                   └─────────────┘
```

## 協議對照表

### CLI 啟動參數

| Copilot SDK 發送 | ACP Proxy 處理 | 說明 |
|-----------------|---------------|------|
| `--headless` | 忽略 | 無 UI 模式 |
| `--server` | 忽略 | Server 模式標記 |
| `--stdio` | 使用 | 啟用 stdio 傳輸 |
| `--log-level <level>` | 可選處理 | 日誌級別 |
| `--port <port>` | 未來支援 | TCP 模式 |
| `--auth-token-env <var>` | 忽略 | 認證相關 |
| `--no-auto-login` | 忽略 | 認證相關 |

### JSON-RPC Methods 對照

#### 狀態查詢

| Copilot Method | ACP 對應 | 轉換邏輯 |
|---------------|---------|---------|
| `ping` | 內部處理 | 直接回應 `{message, timestamp, protocolVersion}` |
| `status.get` | 內部處理 | 回應 `{version, protocolVersion}` |
| `auth.getStatus` | 內部處理 | 回應 `{isAuthenticated: true, authType: "env"}` |
| `models.list` | 內部處理 | 回應後端支援的模型列表 |

#### Session 管理

| Copilot Method | ACP 對應 | 轉換邏輯 |
|---------------|---------|---------|
| `session.create` | `initialize` + `new_session` | 初始化後端連接並建立 session |
| `session.resume` | `new_session` | 恢復 session (可能需模擬) |
| `session.send` | `prompt` | 發送訊息到後端 |
| `session.destroy` | `close` | 關閉 session |
| `session.abort` | `cancel` | 中止當前請求 |
| `session.list` | 內部狀態 | 回應已知的 sessions |
| `session.delete` | 內部處理 | 刪除 session 記錄 |
| `session.getMessages` | 內部狀態 | 回應事件歷史 |
| `session.getLastId` | 內部狀態 | 回應最後的 session ID |

### Events 對照

#### Proxy → Copilot SDK (Notifications)

| ACP Update | Copilot Event Type | 轉換邏輯 |
|-----------|-------------------|---------|
| 連接建立 | `session.start` | Session 初始化完成 |
| `AgentMessageChunk` | `assistant.message` / `assistant.message_delta` | 文字回應 |
| `AgentThoughtChunk` | `assistant.reasoning` / `assistant.reasoning_delta` | 思考過程 |
| `ToolCallStart` | `tool.execution_start` | 工具開始執行 |
| `ToolCallProgress` | `tool.execution_complete` | 工具執行完成 |
| 回應完成 | `assistant.turn_end` + `session.idle` | 輪次結束 |

#### Backend → Proxy → Copilot SDK (Requests)

| ACP Request | Copilot Request | 說明 |
|-------------|-----------------|------|
| `request_permission` | `permission.request` | 權限請求 |
| (custom tools) | `tool.call` | 自訂工具執行 |

### Session Config 對照

```python
# Copilot SDK session.create params
copilot_config = {
    "model": "claude-sonnet-4.5",
    "sessionId": "custom-id",
    "reasoningEffort": "high",
    "tools": [...],
    "systemMessage": {...},
    "provider": {...},          # BYOK - 特殊處理
    "workingDirectory": "/path",
    "streaming": True,
    "mcpServers": {...},
    "requestPermission": True,
    "requestUserInput": True,
    "hooks": True,
}

# 轉換為 ACP new_session params
acp_config = {
    "cwd": "/path",             # workingDirectory
    "mcp_servers": [...],       # mcpServers 轉換
}
```

## 實作計畫

### Phase 1: 最小可行版本 (MVP)

1. **CLI 入口點** (`copilot-acp-proxy`)
   - 接受 `--headless`, `--stdio` 等參數
   - 啟動 JSON-RPC server (stdio 模式)

2. **基本 Methods**
   - `ping` - 心跳
   - `status.get` - 狀態
   - `auth.getStatus` - 認證狀態
   - `session.create` - 建立 session
   - `session.send` - 發送訊息
   - `session.destroy` - 銷毀 session

3. **基本 Events**
   - `session.start`
   - `assistant.message`
   - `assistant.turn_end`
   - `session.idle`

4. **後端連接**
   - 使用 `AcpClient` 連接到後端

### Phase 2: 完整功能

1. **進階 Methods**
   - `session.resume`
   - `session.list`
   - `session.getMessages`
   - `models.list`

2. **工具支援**
   - `tool.call` 請求處理
   - `permission.request` 轉發

3. **Streaming 支援**
   - `assistant.message_delta`
   - `assistant.reasoning_delta`

### Phase 3: 進階功能

1. **TCP 模式** (`--port`)
2. **MCP Server 支援**
3. **BYOK 路由**
4. **多後端支援**

## 檔案結構

```
src/claude_code_acp/
├── proxy/
│   ├── __init__.py
│   ├── server.py           # JSON-RPC Server
│   ├── protocol.py         # Copilot Protocol 定義
│   ├── translator.py       # 協議轉換
│   ├── session_manager.py  # Session 管理
│   └── backend.py          # 後端連接管理
├── cli/
│   └── proxy_cli.py        # CLI 入口點
```

## 測試計畫

1. **單元測試**: 協議轉換
2. **整合測試**: Proxy + Backend
3. **端到端測試**: Copilot SDK → Proxy → Gemini/Claude
