#!/usr/bin/env python3
"""
測試: Copilot SDK (Python) → claude-code-acp Server

執行方式:
    python tests/test_copilot_sdk_claude_server.py

預期結果:
    - 測試 Copilot SDK 是否可以連接到我們的 claude-code-acp server
    - 可能會因為協議差異而失敗

注意:
    - Copilot SDK 使用 JSON-RPC over stdio (與 ACP 相同)
    - 但 Copilot SDK 可能有特定的方法/消息類型
"""
import asyncio
import time
import sys
import os
import platform
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

RESULTS = {
    "system_info": {},
    "sdk_check": None,
    "connect": None,
    "create_session": None,
    "simple_prompt": None,
}


def collect_system_info():
    """收集系統資訊"""
    info = {
        "platform": platform.system(),
        "python_version": platform.python_version(),
    }

    try:
        from claude_code_acp import __version__
        info["claude_code_acp_version"] = __version__
    except:
        info["claude_code_acp_version"] = "unknown"

    try:
        import copilot
        info["copilot_sdk_version"] = copilot.__version__
    except:
        info["copilot_sdk_version"] = "unknown"

    return info


async def main():
    print("=" * 60)
    print("測試: Copilot SDK (Python) → claude-code-acp Server")
    print("=" * 60)

    # Collect system info
    RESULTS["system_info"] = collect_system_info()
    print("\n[系統資訊]")
    for key, value in RESULTS["system_info"].items():
        print(f"  {key}: {value}")

    # Check Copilot SDK
    print("\n[Copilot SDK 檢查]")
    try:
        from copilot import CopilotClient, CopilotSession
        print("  ✅ Copilot SDK 已安裝")
        RESULTS["sdk_check"] = True
    except ImportError as e:
        print(f"  ❌ Copilot SDK 未安裝: {e}")
        RESULTS["sdk_check"] = False
        return False

    # Check claude-code-acp
    claude_acp_path = shutil.which("claude-code-acp")
    if not claude_acp_path:
        print("  ❌ claude-code-acp 未找到")
        return False
    print(f"  ✅ claude-code-acp 路徑: {claude_acp_path}")

    # Try to connect using Copilot SDK with our server
    print("\n[TEST 1] 使用 Copilot SDK 連接 claude-code-acp")

    try:
        # Create client with our claude-code-acp as the CLI
        client = CopilotClient({
            "cli_path": claude_acp_path,
            "cwd": "/tmp",
            "use_stdio": True,
            "auto_start": True,
        })

        # Start the client
        t1 = time.time()
        await asyncio.wait_for(client.start(), timeout=30.0)
        connect_time = time.time() - t1
        RESULTS["connect"] = {"time": connect_time, "pass": True}
        print(f"  連接時間: {connect_time:.2f}s ✅")

        # Try to get status
        print("\n[TEST 2] 取得狀態")
        try:
            status = await asyncio.wait_for(client.get_status(), timeout=10.0)
            print(f"  狀態: {status}")
        except Exception as e:
            print(f"  狀態取得失敗 (可能協議不同): {e}")

        # Try to create session
        print("\n[TEST 3] 建立 Session")
        try:
            session = await asyncio.wait_for(
                client.create_session({"cwd": "/tmp"}),
                timeout=30.0
            )
            RESULTS["create_session"] = {"pass": True}
            print(f"  Session 建立成功 ✅")

            # Try to send a message
            print("\n[TEST 4] 發送訊息")
            try:
                # Register event handlers
                received_text = []

                @session.on("text")
                def on_text(text):
                    received_text.append(text)
                    print(f"  [TEXT] {text[:50]}...")

                @session.on("complete")
                def on_complete():
                    print("  [COMPLETE]")

                # Send message
                await asyncio.wait_for(
                    session.send_message("Say hello!"),
                    timeout=60.0
                )

                RESULTS["simple_prompt"] = {
                    "pass": len(received_text) > 0,
                    "response": "".join(received_text)[:200],
                }
                print(f"  訊息發送: {'✅' if received_text else '❌'}")

            except Exception as e:
                print(f"  訊息發送失敗: {e}")
                RESULTS["simple_prompt"] = {"pass": False, "error": str(e)}

        except Exception as e:
            print(f"  Session 建立失敗: {e}")
            RESULTS["create_session"] = {"pass": False, "error": str(e)}

        # Stop client
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

    tests = [
        ("連接測試", "connect"),
        ("Session 建立", "create_session"),
        ("訊息發送", "simple_prompt"),
    ]

    for name, key in tests:
        result = RESULTS.get(key)
        if result and result.get("pass"):
            time_str = f" ({result.get('time', 0):.2f}s)" if "time" in result else ""
            print(f"{name}: ✅ PASS{time_str}")
        elif result:
            print(f"{name}: ❌ FAIL - {result.get('error', 'unknown')[:50]}")
        else:
            print(f"{name}: ⏭️ SKIPPED")

    print("\n" + "=" * 60)
    print("注意: Copilot SDK 和 ACP 協議可能有差異")
    print("這個測試主要是探索性質的")
    print("=" * 60)

    return RESULTS.get("connect", {}).get("pass", False)


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
