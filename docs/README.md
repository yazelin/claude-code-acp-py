# ACP Server 使用指南

本目錄包含各家 ACP Server 的使用指南和注意事項。

## 支援的 ACP Servers

| Server | 文件 | 狀態 |
|--------|------|------|
| [Gemini CLI](./gemini-acp.md) | gemini-acp.md | ✅ 測試通過 |
| [GitHub Copilot](./copilot-acp.md) | copilot-acp.md | 🔄 實驗性 |
| [claude-code-acp](./claude-code-acp.md) | claude-code-acp.md | ✅ 完整支援 |

## MCP 配置

各 ACP Server 對 MCP (Model Context Protocol) 的支援方式不同：

| Server | 動態 MCP | 預配置 MCP | 說明 |
|--------|----------|-----------|------|
| claude-code-acp | ✅ | ✅ | 通過 `mcp_servers` 參數傳入 |
| Gemini CLI | ❌ | ✅ | 需用 `gemini mcp add` 預配置 |
| GitHub Copilot | ❓ | ❓ | 待測試 |

詳見 [MCP 配置指南](./mcp-configuration.md)

## 快速參考

```python
from claude_code_acp import AcpClient

# Claude (本套件)
claude = AcpClient(command="claude-code-acp")

# Gemini (需等 ~12s 初始化)
gemini = AcpClient(command="gemini", args=["--experimental-acp"])

# Gemini + MCP
gemini_mcp = AcpClient(
    command="gemini",
    args=["--experimental-acp", "--allowed-mcp-server-names", "nanobanana"]
)

# Copilot (實驗性)
copilot = AcpClient(command="copilot", args=["--acp"])
```
