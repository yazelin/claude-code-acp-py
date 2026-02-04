# 測試記錄

## 測試環境

```
Platform: Linux
Platform Version: #37~24.04.1-Ubuntu SMP
Python: 3.11.13
claude-code-acp: v0.3.6
Gemini CLI: 0.26.0
測試日期: 2025-02-04
```

## 測試結果總覽

| 測試項目 | 狀態 | 說明 |
|---------|------|------|
| [AcpClient → claude-code-acp](./test_acp_client_claude.py) | ✅ PASS | 基本功能 + Tool use |
| [AcpClient → claude-code-acp + MCP](./test_acp_client_claude_mcp.py) | ⚠️ 需 API Key | 動態 MCP 配置 |
| [AcpClient → Gemini ACP](./test_acp_client_gemini.py) | ✅ PASS | 基本功能 |
| [AcpClient → Gemini + MCP](./test_acp_client_gemini_mcp.py) | ✅ PASS | 需預配置 MCP |
| AcpClient → Copilot ACP | 🔄 待測試 | - |

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
gemini mcp add nanobanana "uvx nanobanana"
```

| 功能 | 結果 | 說明 |
|------|------|------|
| MCP 動態配置 | ❌ | Gemini 不支援 |
| MCP 預配置 + flag | ✅ | 使用 --allowed-mcp-server-names |
| MCP tools 可用 | ✅ | 顯示 nanobanana tools |

## 已知限制

1. **Gemini 初始化慢**: ~12 秒
2. **Gemini 不支援動態 MCP**: 需用 CLI 預配置
3. **斷開連接警告**: 正常現象，不影響功能
