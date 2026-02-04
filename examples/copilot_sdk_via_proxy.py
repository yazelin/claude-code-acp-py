#!/usr/bin/env python3
"""
Copilot SDK 透過 ACP Proxy 連接不同後端的範例

使用方式:
    # 先安裝依賴
    uv pip install github-copilot-sdk
    uv pip install -e .

    # 連接 Claude
    ACP_PROXY_BACKEND=claude-code-acp uv run python examples/copilot_sdk_via_proxy.py

    # 連接 Gemini
    ACP_PROXY_BACKEND=gemini uv run python examples/copilot_sdk_via_proxy.py

    # 連接 Copilot
    ACP_PROXY_BACKEND=copilot uv run python examples/copilot_sdk_via_proxy.py
"""
import asyncio
import os
import shutil
import sys

async def main():
    # 檢查依賴
    try:
        from copilot import CopilotClient
    except ImportError:
        print("❌ 請先安裝 Copilot SDK:")
        print("   uv pip install github-copilot-sdk")
        sys.exit(1)

    # 檢查 proxy
    proxy_path = shutil.which("copilot-acp-proxy")
    if not proxy_path:
        print("❌ 找不到 copilot-acp-proxy")
        print("   請先安裝: uv pip install -e .")
        sys.exit(1)

    # 取得後端設定，並確保環境變數有設定（給 proxy 子程序用）
    backend = os.environ.get("ACP_PROXY_BACKEND", "claude-code-acp")
    os.environ["ACP_PROXY_BACKEND"] = backend  # 確保傳給 proxy 子程序

    print("=" * 50)
    print(f"Copilot SDK → ACP Proxy → {backend}")
    print("=" * 50)
    print(f"Proxy: {proxy_path}")
    print(f"Backend: {backend}")

    # 建立 client
    client = CopilotClient({"cli_path": proxy_path})

    print("\n[1] 啟動 Client...")
    await client.start()
    print("    ✅ 成功")

    # 根據後端選擇模型
    # 注意: claude-code-acp 只支援 'opus' 和 'sonnet' 作為 alias
    model_map = {
        "gemini": "gemini-2.5-flash",
        "claude-code-acp": "sonnet",  # 或 "opus"
        "copilot": "gpt-4o",
    }
    model = model_map.get(backend, "default")

    print(f"\n[2] 建立 Session (model: {model})...")
    session = await client.create_session({"model": model})
    print("    ✅ 成功")

    # 設定事件處理
    response_text = []
    done = asyncio.Event()

    def on_event(event):
        event_type = event.type.value if hasattr(event.type, 'value') else str(event.type)

        # Debug: 顯示所有事件類型和資料
        if os.environ.get("DEBUG"):
            print(f"\n    [DEBUG] Event: {event_type}", file=sys.stderr)
            if event_type == "assistant.message_delta":
                print(f"    [DEBUG] Data: {event.data}", file=sys.stderr)

        if event_type == "assistant.message":
            content = event.data.content if hasattr(event.data, 'content') else str(event.data)
            if content and content not in response_text:
                response_text.append(content)
                print(content, end="", flush=True)
        elif event_type == "assistant.message_delta":
            # 嘗試多種方式取得 delta 內容
            delta = None
            if hasattr(event.data, 'deltaContent'):
                delta = event.data.deltaContent
            elif hasattr(event.data, 'delta_content'):
                delta = event.data.delta_content
            elif isinstance(event.data, dict):
                delta = event.data.get('deltaContent') or event.data.get('delta_content')

            if delta:
                print(delta, end="", flush=True)
                response_text.append(delta)
        elif event_type == "tool.execution_start":
            tool = event.data.toolName if hasattr(event.data, 'toolName') else "unknown"
            print(f"\n    🔧 Tool: {tool}")
        elif event_type == "session.idle":
            # 延遲一下讓最後的 message 事件有機會處理
            asyncio.get_event_loop().call_later(0.5, done.set)

    session.on(on_event)

    # 互動迴圈
    print("\n[3] 開始對話 (輸入 'quit' 結束)")
    print("-" * 50)

    while True:
        try:
            prompt = input("\n你: ").strip()
            if not prompt:
                continue
            if prompt.lower() in ('quit', 'exit', 'q'):
                break

            response_text.clear()
            done.clear()

            print("\nAI: ", end="", flush=True)
            await session.send({"prompt": prompt})

            try:
                await asyncio.wait_for(done.wait(), timeout=120.0)
            except asyncio.TimeoutError:
                print("\n    ⚠️ 回應超時")

            # 如果沒有 streaming，顯示完整回應
            if response_text and not any('\n' in t for t in response_text):
                print("".join(response_text))

        except KeyboardInterrupt:
            print("\n\n中斷")
            break
        except Exception as e:
            print(f"\n    ❌ 錯誤: {e}")

    # 清理
    print("\n[4] 清理...")
    await session.destroy()
    await client.stop()
    print("    ✅ 完成")

if __name__ == "__main__":
    asyncio.run(main())
