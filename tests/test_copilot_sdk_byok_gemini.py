#!/usr/bin/env python3
"""
測試: Copilot SDK + BYOK → Gemini API (HTTP)

執行方式:
    python tests/test_copilot_sdk_byok_gemini.py

前置條件:
    - pip install github-copilot-sdk
    - 設定 GEMINI_API_KEY 環境變數

架構:
    Copilot SDK → Copilot CLI (ACP/stdio) → Gemini API (HTTP)

注意:
    - 這不是連接 Gemini CLI 的 ACP server
    - 這是透過 BYOK 直接呼叫 Gemini 的 HTTP API
    - Gemini API 有 OpenAI 相容模式
"""
import asyncio
import time
import sys
import os
import platform
import shutil

RESULTS = {
    "system_info": {},
    "copilot_cli_check": None,
    "api_key_check": None,
    "connect": None,
    "byok_gemini": None,
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


def check_copilot_cli():
    """檢查 Copilot CLI 是否可用"""
    copilot_path = shutil.which("copilot")
    if not copilot_path:
        return {"available": False, "error": "copilot not found in PATH"}

    try:
        import subprocess
        result = subprocess.run(
            ["copilot", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return {"available": True, "path": copilot_path, "version": result.stdout.strip().split('\n')[0]}
        else:
            return {"available": False, "error": result.stderr}
    except Exception as e:
        return {"available": False, "error": str(e)}


async def main():
    print("=" * 60)
    print("測試: Copilot SDK + BYOK → Gemini API")
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
        print("  安裝方式: pip install github-copilot-sdk")
        return False

    # Check Copilot CLI (required for BYOK)
    print("\n[Copilot CLI 檢查]")
    RESULTS["copilot_cli_check"] = check_copilot_cli()
    if RESULTS["copilot_cli_check"]["available"]:
        print(f"  ✅ Copilot CLI 可用: {RESULTS['copilot_cli_check'].get('version', 'unknown')}")
    else:
        print(f"  ❌ Copilot CLI 不可用: {RESULTS['copilot_cli_check'].get('error')}")
        print("  BYOK 需要 Copilot CLI")
        return False

    # Check API key
    print("\n[API Key 檢查]")
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("NANOBANANA_GEMINI_API_KEY")
    if api_key:
        print(f"  ✅ Gemini API Key 已設定 ({api_key[:8]}...)")
        RESULTS["api_key_check"] = True
    else:
        print("  ❌ Gemini API Key 未設定")
        print("  設定方式: export GEMINI_API_KEY=your-key")
        return False

    # Test BYOK with Gemini API
    print("\n[TEST] Copilot SDK + BYOK → Gemini API")
    print("  架構: SDK → Copilot CLI (ACP) → Gemini API (HTTP)")

    try:
        client = CopilotClient()

        # Start client
        print("  啟動 Copilot Client...")
        t1 = time.time()
        await asyncio.wait_for(client.start(), timeout=30.0)
        connect_time = time.time() - t1
        RESULTS["connect"] = {"time": connect_time, "pass": True}
        print(f"  連接時間: {connect_time:.2f}s ✅")

        # Create session with BYOK pointing to Gemini API
        # Gemini API has OpenAI-compatible endpoint
        # https://ai.google.dev/gemini-api/docs/openai
        print("\n  建立 BYOK Session (Gemini API)...")

        session = await asyncio.wait_for(
            client.create_session({
                "model": "gemini-2.0-flash",
                "provider": {
                    "type": "openai",  # Gemini API 支援 OpenAI 相容模式
                    "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
                    "api_key": api_key,
                },
            }),
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
            elif event_type == "session.idle":
                done.set()

        session.on(on_event)

        t2 = time.time()
        await session.send({"prompt": "Say 'Hello from Gemini!' in one short sentence."})
        await asyncio.wait_for(done.wait(), timeout=60.0)
        response_time = time.time() - t2

        full_response = "".join(response_text)
        RESULTS["byok_gemini"] = {
            "pass": len(full_response) > 0,
            "time": response_time,
            "response": full_response[:200],
        }
        print(f"  回應時間: {response_time:.2f}s")
        print(f"  BYOK Gemini: {'✅' if full_response else '❌'}")

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

    if RESULTS.get("byok_gemini"):
        status = "✅ PASS" if RESULTS["byok_gemini"]["pass"] else "❌ FAIL"
        time_str = f" ({RESULTS['byok_gemini']['time']:.2f}s)" if "time" in RESULTS["byok_gemini"] else ""
        print(f"BYOK Gemini API: {status}{time_str}")
    else:
        print("BYOK Gemini API: ❌ FAIL")

    all_pass = (
        RESULTS.get("connect", {}).get("pass", False) and
        RESULTS.get("byok_gemini", {}).get("pass", False)
    )

    print("\n" + "=" * 60)
    if all_pass:
        print("🎉 測試通過!")
        print("\n結論:")
        print("  Copilot SDK 可以透過 BYOK 連接 Gemini API (HTTP)")
        print("  這跟連接 Gemini CLI ACP server 是不同的架構")
    else:
        print("⚠️ 測試失敗")
        if RESULTS.get("error"):
            print(f"  錯誤: {RESULTS['error']}")
    print("=" * 60)

    return all_pass


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
