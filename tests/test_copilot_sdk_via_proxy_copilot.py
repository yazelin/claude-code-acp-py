#!/usr/bin/env python3
"""
測試: Copilot SDK → ACP Proxy → Copilot CLI

執行方式:
    uv run python tests/test_copilot_sdk_via_proxy_copilot.py

前置條件:
    - uv pip install github-copilot-sdk
    - 安裝本套件 (uv pip install -e .)
    - 安裝 Copilot CLI (npm install -g @anthropic-ai/copilot-cli 或 GitHub Copilot)
    - GitHub 認證 (gh auth login)

架構:
    Copilot SDK → copilot-acp-proxy (我們的) → copilot --acp

這個測試驗證:
    1. Copilot SDK 能夠連接到我們的 Proxy
    2. Proxy 能夠轉發請求到 Copilot CLI
    3. 回應能夠正確傳回 Copilot SDK

注意: 這個測試主要用於驗證架構的完整性
      實際上 Copilot SDK 可以直接連接 Copilot CLI
"""
import asyncio
import time
import sys
import os
import platform
import shutil

RESULTS = {
    "system_info": {},
    "proxy_check": None,
    "backend_check": None,
    "connect": None,
    "simple_prompt": None,
}


def collect_system_info():
    """收集系統資訊"""
    info = {
        "platform": platform.system(),
        "python_version": platform.python_version(),
    }

    try:
        import copilot
        info["copilot_sdk_version"] = getattr(copilot, "__version__", "unknown")
    except ImportError:
        info["copilot_sdk_version"] = "not installed"

    return info


def check_proxy():
    """檢查 ACP Proxy 是否可用"""
    proxy_path = shutil.which("copilot-acp-proxy")
    if proxy_path:
        return {"available": True, "path": proxy_path}

    # Try running from module
    try:
        import subprocess
        result = subprocess.run(
            [sys.executable, "-m", "claude_code_acp.proxy.cli", "--help"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return {"available": True, "path": "python -m claude_code_acp.proxy.cli"}
    except:
        pass

    return {"available": False, "error": "copilot-acp-proxy not found"}


def check_backend(backend: str):
    """檢查後端 CLI 是否可用"""
    path = shutil.which(backend)
    if not path:
        return {"available": False, "error": f"{backend} not found in PATH"}
    return {"available": True, "path": path}


async def main():
    print("=" * 60)
    print("測試: Copilot SDK → ACP Proxy → Copilot CLI")
    print("=" * 60)

    # Collect system info
    RESULTS["system_info"] = collect_system_info()
    print("\n[系統資訊]")
    for key, value in RESULTS["system_info"].items():
        print(f"  {key}: {value}")

    # Check Copilot SDK
    print("\n[Copilot SDK 檢查]")
    try:
        from copilot import CopilotClient
        print("  ✅ Copilot SDK 已安裝")
    except ImportError as e:
        print(f"  ❌ Copilot SDK 未安裝: {e}")
        print("  安裝方式: uv pip install github-copilot-sdk")
        return False

    # Check ACP Proxy
    print("\n[ACP Proxy 檢查]")
    RESULTS["proxy_check"] = check_proxy()
    if RESULTS["proxy_check"]["available"]:
        print(f"  ✅ ACP Proxy 可用: {RESULTS['proxy_check']['path']}")
    else:
        print(f"  ❌ ACP Proxy 不可用: {RESULTS['proxy_check'].get('error')}")
        print("  安裝方式: uv pip install -e .")
        return False

    # Check backend (copilot)
    backend = "copilot"
    print(f"\n[Backend 檢查: {backend}]")
    RESULTS["backend_check"] = check_backend(backend)
    if RESULTS["backend_check"]["available"]:
        print(f"  ✅ {backend} 可用: {RESULTS['backend_check']['path']}")
    else:
        print(f"  ❌ {backend} 不可用: {RESULTS['backend_check'].get('error')}")
        return False

    # Test: Copilot SDK → ACP Proxy → Copilot CLI
    print("\n[TEST] Copilot SDK → ACP Proxy → Copilot CLI")

    # Determine proxy path
    proxy_path = shutil.which("copilot-acp-proxy")
    if not proxy_path:
        print("  ❌ copilot-acp-proxy not found")
        return False

    print(f"  Proxy: {proxy_path}")

    # Python SDK doesn't have cli_args, so we use environment variable
    os.environ["ACP_PROXY_BACKEND"] = "copilot"
    os.environ["ACP_PROXY_LOG_LEVEL"] = "debug"

    try:
        # Create Copilot client with our proxy as the CLI
        # SDK will add: --headless --log-level info --stdio
        client = CopilotClient({
            "cli_path": proxy_path,
            "log_level": "debug",
        })

        # Start client
        print("  啟動 Copilot Client (via Proxy)...")
        t1 = time.time()
        await asyncio.wait_for(client.start(), timeout=60.0)
        connect_time = time.time() - t1
        RESULTS["connect"] = {"time": connect_time, "pass": True}
        print(f"  連接時間: {connect_time:.2f}s ✅")

        # Create session
        print("\n  建立 Session...")
        session = await asyncio.wait_for(
            client.create_session({"model": "gpt-4o"}),
            timeout=30.0
        )
        print("  Session 建立成功 ✅")

        # Send a test message
        print("\n  發送測試訊息...")
        response_text = []
        done = asyncio.Event()

        def on_event(event):
            event_type = event.type.value if hasattr(event.type, 'value') else str(event.type)
            if event_type == "assistant.message":
                content = event.data.content if hasattr(event.data, 'content') else str(event.data)
                response_text.append(content)
                print(f"  [回應] {content[:100]}...")
            elif event_type == "assistant.message_delta":
                delta = event.data.deltaContent if hasattr(event.data, 'deltaContent') else ""
                if delta:
                    response_text.append(delta)
            elif event_type == "session.idle":
                done.set()

        session.on(on_event)

        t2 = time.time()
        await session.send({"prompt": "Say 'Hello from Copilot via Proxy!' in one short sentence."})
        await asyncio.wait_for(done.wait(), timeout=120.0)
        response_time = time.time() - t2

        full_response = "".join(response_text)
        RESULTS["simple_prompt"] = {
            "pass": len(full_response) > 0,
            "time": response_time,
            "response": full_response[:200],
        }
        print(f"  回應時間: {response_time:.2f}s")
        print(f"  Prompt 測試: {'✅' if full_response else '❌'}")

        # Cleanup
        await session.destroy()
        await client.stop()

    except asyncio.TimeoutError:
        print("  ❌ TIMEOUT")
        RESULTS["error"] = "timeout"
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        RESULTS["error"] = str(e)
        import traceback
        traceback.print_exc()

    # Summary
    print("\n" + "=" * 60)
    print("測試結果總覽")
    print("=" * 60)

    if RESULTS["connect"]:
        print(f"連接測試: ✅ PASS ({RESULTS['connect']['time']:.2f}s)")
    else:
        print("連接測試: ❌ FAIL")

    if RESULTS.get("simple_prompt"):
        status = "✅ PASS" if RESULTS["simple_prompt"]["pass"] else "❌ FAIL"
        time_str = f" ({RESULTS['simple_prompt']['time']:.2f}s)" if "time" in RESULTS["simple_prompt"] else ""
        print(f"簡單 Prompt: {status}{time_str}")
    else:
        print("簡單 Prompt: ❌ FAIL")

    all_pass = (
        RESULTS.get("connect", {}).get("pass", False) and
        RESULTS.get("simple_prompt", {}).get("pass", False)
    )

    print("\n" + "=" * 60)
    if all_pass:
        print("🎉 測試通過!")
        print("\n結論:")
        print("  Copilot SDK 可以透過 ACP Proxy 連接到 Copilot CLI!")
        print("  架構: Copilot SDK → copilot-acp-proxy → copilot --acp")
        print("\n  注意: 這主要是驗證架構完整性")
        print("  實際上 Copilot SDK 可以直接連接 Copilot CLI")
    else:
        print("⚠️ 測試失敗")
        if RESULTS.get("error"):
            print(f"  錯誤: {RESULTS['error']}")
    print("=" * 60)

    return all_pass


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
