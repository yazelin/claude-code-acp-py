#!/usr/bin/env python3
"""
測試: AcpClient → Gemini ACP

執行方式:
    python tests/test_acp_client_gemini.py

預期結果:
    - 連接成功 (~12s 初始化)
    - 簡單 prompt 回應正確
    - on_text, on_thinking, on_complete events 正常

注意:
    - Gemini 初始化需要約 12 秒
    - 需要 Gemini CLI 已安裝並認證
"""
import asyncio
import time
import sys
import os
import platform

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

RESULTS = {
    "system_info": {},
    "connect": None,
    "simple_prompt": None,
    "events": {
        "on_text": False,
        "on_thinking": False,
        "on_complete": False,
    },
}


def collect_system_info():
    """收集系統資訊"""
    import subprocess

    info = {
        "platform": platform.system(),
        "platform_version": platform.version(),
        "python_version": platform.python_version(),
        "machine": platform.machine(),
    }

    # Get package version
    try:
        from claude_code_acp import __version__
        info["claude_code_acp_version"] = __version__
    except:
        info["claude_code_acp_version"] = "unknown"

    # Get gemini version
    try:
        result = subprocess.run(["gemini", "--version"], capture_output=True, text=True, timeout=5)
        info["gemini_version"] = result.stdout.strip() or result.stderr.strip()
    except:
        info["gemini_version"] = "unknown"

    return info


async def main():
    print("=" * 60)
    print("測試: AcpClient → Gemini ACP")
    print("=" * 60)

    # Collect system info
    RESULTS["system_info"] = collect_system_info()
    print("\n[系統資訊]")
    for key, value in RESULTS["system_info"].items():
        print(f"  {key}: {value}")

    from claude_code_acp import AcpClient

    client = AcpClient(
        command="gemini",
        args=["--experimental-acp"],
        cwd="/tmp",
    )

    @client.on_text
    async def on_text(text):
        RESULTS["events"]["on_text"] = True

    @client.on_thinking
    async def on_thinking(text):
        RESULTS["events"]["on_thinking"] = True
        print(f"  [THINK] {text[:50]}...")

    @client.on_complete
    async def on_complete():
        RESULTS["events"]["on_complete"] = True

    try:
        # Test 1: Connect (includes ~12s initialization)
        print("\n[TEST 1] 連接測試 (Gemini 需要 ~12s 初始化)")
        t1 = time.time()
        await asyncio.wait_for(client.connect(), timeout=60.0)
        connect_time = time.time() - t1
        # Gemini takes ~12s, so we allow up to 30s
        RESULTS["connect"] = {"time": connect_time, "pass": connect_time < 30}
        print(f"  連接時間: {connect_time:.2f}s {'✅' if RESULTS['connect']['pass'] else '❌'}")

        # Test 2: Simple prompt
        print("\n[TEST 2] 簡單 prompt")
        t2 = time.time()
        response = await asyncio.wait_for(
            client.prompt("Say 'hello' in one word."),
            timeout=30.0
        )
        prompt_time = time.time() - t2
        is_correct = "hello" in response.lower()
        RESULTS["simple_prompt"] = {"time": prompt_time, "response": response.strip()[:100], "pass": is_correct}
        print(f"  回應: '{response.strip()[:50]}...' {'✅' if is_correct else '❌'}")
        print(f"  耗時: {prompt_time:.2f}s")

        await client.disconnect()

    except asyncio.TimeoutError:
        print("  ❌ TIMEOUT")
        RESULTS["error"] = "timeout"
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        RESULTS["error"] = str(e)

    # Summary
    print("\n" + "=" * 60)
    print("測試結果總覽")
    print("=" * 60)

    all_pass = True

    if RESULTS["connect"]:
        status = "✅ PASS" if RESULTS["connect"]["pass"] else "❌ FAIL"
        print(f"連接測試: {status} ({RESULTS['connect']['time']:.2f}s)")
        all_pass = all_pass and RESULTS["connect"]["pass"]

    if RESULTS["simple_prompt"]:
        status = "✅ PASS" if RESULTS["simple_prompt"]["pass"] else "❌ FAIL"
        print(f"簡單 prompt: {status}")
        all_pass = all_pass and RESULTS["simple_prompt"]["pass"]

    print(f"\nEvents:")
    for event, triggered in RESULTS["events"].items():
        print(f"  {event}: {'✅' if triggered else '❌'}")
        if event != "on_thinking":  # thinking is optional
            all_pass = all_pass and triggered

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
