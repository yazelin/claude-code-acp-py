# GitHub Copilot ACP 使用指南

## 概述

GitHub Copilot CLI 支援 ACP 模式，可以通過 `AcpClient` 連接使用。

**狀態**: 🔄 實驗性 (待完整測試)

## 安裝

```bash
# 需要 GitHub Copilot CLI
# 通常隨 GitHub CLI 一起安裝
gh extension install github/gh-copilot
```

## 基本用法

```python
import asyncio
from claude_code_acp import AcpClient

async def main():
    client = AcpClient(
        command="copilot",
        args=["--acp"],
        cwd="/your/working/directory",
    )

    @client.on_text
    async def on_text(text):
        print(text, end="", flush=True)

    @client.on_complete
    async def on_complete():
        print("\n--- 完成 ---")

    async with client:
        response = await client.prompt("Hello, Copilot!")
        print(f"\n回應: {response}")

asyncio.run(main())
```

## ⚠️ 注意事項

### 1. 實驗性功能

Copilot 的 ACP 支援仍是實驗性功能，API 可能會改變。

### 2. 認證

需要先登入 GitHub：

```bash
gh auth login
```

### 3. 可能的 CLI 參數

```bash
# 常見參數 (請查閱最新文件)
copilot --acp           # 啟用 ACP 模式
copilot --debug         # 除錯模式
```

## MCP 配置

⚠️ **待測試** - Copilot 對 MCP 的支援情況尚未完整測試。

## 與 Gemini 的差異

| 特性 | Copilot | Gemini |
|------|---------|--------|
| ACP 參數 | `--acp` | `--experimental-acp` |
| 初始化時間 | 待測試 | ~12 秒 |
| MCP 支援 | 待測試 | 需預配置 |
| 認證方式 | GitHub OAuth | Google Account |

## 測試結果

| 功能 | 狀態 | 備註 |
|------|------|------|
| 基本連接 | 🔄 | 待完整測試 |
| Prompt/Response | 🔄 | 待完整測試 |
| MCP | 🔄 | 待完整測試 |

## 貢獻

如果你有 Copilot ACP 的測試結果，歡迎提交 PR 更新此文件！
