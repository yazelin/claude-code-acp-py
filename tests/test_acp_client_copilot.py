#!/usr/bin/env python3
"""
測試: AcpClient → Copilot CLI ACP Server

執行方式:
    python tests/test_acp_client_copilot.py

前置條件:
    - 安裝 GitHub Copilot CLI
    - 已登入 GitHub (gh auth login)

預期結果:
    - 連接成功
    - 基本 prompt 回應正常
    - Tool use 可用
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
    "copilot_check": None,
    "connect": None,
    "simple_prompt": None,
    "tool_use": None,
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

    # Get Copilot version
    try:
        import subprocess
        result = subprocess.run(
            ["copilot", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        info["copilot_version"] = result.stdout.strip().split('\n')[0]
    except:
        info["copilot_version"] = "unknown"

    return info


def check_copilot():
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
            return {"available": True, "path": copilot_path, "version": result.stdout.strip()}
        else:
            return {"available": False, "error": result.stderr}
    except Exception as e:
        return {"available": False, "error": str(e)}


async def main():
    print("=" * 60)
    print("測試: AcpClient → Copilot CLI ACP Server")
    print("=" * 60)

    # Collect system info
    RESULTS["system_info"] = collect_system_info()
    print("\n[系統資訊]")
    for key, value in RESULTS["system_info"].items():
        print(f"  {key}: {value}")

    # Check Copilot CLI
    print("\n[Copilot CLI 檢查]")
    RESULTS["copilot_check"] = check_copilot()
    if RESULTS["copilot_check"]["available"]:
        print(f"  ✅ Copilot CLI 可用")
        print(f"  路徑: {RESULTS['copilot_check']['path']}")
    else:
        print(f"  ❌ Copilot CLI 不可用: {RESULTS['copilot_check'].get('error')}")
        print("\n" + "=" * 60)
        print("⚠️ 測試跳過: Copilot CLI 未安裝")
        print("=" * 60)
        return False

    from claude_code_acp import AcpClient

    client = AcpClient(
        command="copilot",
        args=["--acp"],
        cwd="/tmp",
    )

    received_text = []
    tool_calls = []

    @client.on_text
    async def on_text(text):
        received_text.append(text)

    @client.on_thinking
    async def on_thinking(text):
        print(f"  [THINK] {text[:50]}...")

    @client.on_tool_start
    async def on_tool_start(tool_id, name, input_data):
        print(f"  [TOOL] {name}")
        tool_calls.append(name)

    @client.on_permission
    async def on_permission(name, input_data, options):
        print(f"  [PERM] {name} -> allow")
        return "allow"

    try:
        # Test 1: Connect
        print("\n[TEST 1] 連接")
        t1 = time.time()
        await asyncio.wait_for(client.connect(), timeout=30.0)
        connect_time = time.time() - t1
        RESULTS["connect"] = {"time": connect_time, "pass": True}
        print(f"  連接時間: {connect_time:.2f}s ✅")

        # Test 2: Simple prompt
        print("\n[TEST 2] 簡單 prompt")
        received_text.clear()
        t2 = time.time()
        response = await asyncio.wait_for(
            client.prompt("Say 'Hello from Copilot!' and nothing else."),
            timeout=60.0
        )
        prompt_time = time.time() - t2
        has_response = len(response) > 0
        RESULTS["simple_prompt"] = {
            "time": prompt_time,
            "pass": has_response,
            "response": response[:200],
        }
        print(f"  回應時間: {prompt_time:.2f}s {'✅' if has_response else '❌'}")
        print(f"  回應: {response[:100]}...")

        # Test 3: Tool use
        print("\n[TEST 3] Tool use (ls /tmp)")
        tool_calls.clear()
        t3 = time.time()
        response = await asyncio.wait_for(
            client.prompt("List the files in /tmp directory. Use the appropriate tool."),
            timeout=60.0
        )
        tool_time = time.time() - t3
        has_tool = len(tool_calls) > 0
        RESULTS["tool_use"] = {
            "time": tool_time,
            "pass": has_tool,
            "tools": tool_calls[:5],
        }
        print(f"  工具使用: {'✅' if has_tool else '❌'}")
        if tool_calls:
            print(f"  使用的工具: {', '.join(tool_calls[:3])}")

        await client.disconnect()

    except asyncio.TimeoutError as e:
        print(f"  ❌ TIMEOUT: {e}")
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
        ("簡單 prompt", "simple_prompt"),
        ("Tool use", "tool_use"),
    ]

    all_pass = True
    for name, key in tests:
        result = RESULTS.get(key)
        if result and result.get("pass"):
            time_str = f" ({result.get('time', 0):.2f}s)" if "time" in result else ""
            print(f"{name}: ✅ PASS{time_str}")
        else:
            print(f"{name}: ❌ FAIL")
            all_pass = False

    print("\n" + "=" * 60)
    if all_pass:
        print("🎉 所有測試通過!")
    else:
        print("⚠️ 部分測試失敗")
    print("=" * 60)

    return all_pass


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
