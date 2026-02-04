#!/usr/bin/env python3
"""
測試: AcpClient → claude-code-acp (our server)

執行方式:
    python tests/test_acp_client_claude.py

預期結果:
    - 連接成功 (~1-2s)
    - 簡單 prompt 回應正確
    - Tool use 正常執行
    - 所有 events 正常觸發
"""
import asyncio
import time
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Test results
RESULTS = {
    "connect": None,
    "simple_prompt": None,
    "tool_use": None,
    "events": {
        "on_text": False,
        "on_tool_start": False,
        "on_tool_end": False,
        "on_complete": False,
    },
}


async def main():
    print("=" * 60)
    print("測試: AcpClient → claude-code-acp")
    print("=" * 60)

    from claude_code_acp import AcpClient

    client = AcpClient(
        command="claude-code-acp",
        cwd="/tmp",
    )

    @client.on_text
    async def on_text(text):
        RESULTS["events"]["on_text"] = True

    @client.on_thinking
    async def on_thinking(text):
        pass

    @client.on_tool_start
    async def on_tool_start(tool_id, name, input_data):
        RESULTS["events"]["on_tool_start"] = True
        print(f"  [TOOL] {name}")

    @client.on_tool_end
    async def on_tool_end(tool_id, status, output):
        RESULTS["events"]["on_tool_end"] = True

    @client.on_permission
    async def on_permission(name, input_data, options):
        return "allow"

    @client.on_complete
    async def on_complete():
        RESULTS["events"]["on_complete"] = True

    try:
        # Test 1: Connect
        print("\n[TEST 1] 連接測試")
        t1 = time.time()
        await client.connect()
        connect_time = time.time() - t1
        RESULTS["connect"] = {"time": connect_time, "pass": connect_time < 10}
        print(f"  連接時間: {connect_time:.2f}s {'✅' if RESULTS['connect']['pass'] else '❌'}")

        # Test 2: Simple prompt
        print("\n[TEST 2] 簡單 prompt (2+2=?)")
        t2 = time.time()
        response = await asyncio.wait_for(
            client.prompt("What is 2+2? Reply with just the number, nothing else."),
            timeout=30.0
        )
        prompt_time = time.time() - t2
        is_correct = "4" in response
        RESULTS["simple_prompt"] = {"time": prompt_time, "response": response.strip(), "pass": is_correct}
        print(f"  回應: '{response.strip()}' {'✅' if is_correct else '❌'}")
        print(f"  耗時: {prompt_time:.2f}s")

        # Test 3: Tool use
        print("\n[TEST 3] Tool use (ls /tmp)")
        t3 = time.time()
        response2 = await asyncio.wait_for(
            client.prompt("Run 'ls /tmp | head -3' and show the output."),
            timeout=60.0
        )
        tool_time = time.time() - t3
        tool_worked = RESULTS["events"]["on_tool_start"] and RESULTS["events"]["on_tool_end"]
        RESULTS["tool_use"] = {"time": tool_time, "pass": tool_worked}
        print(f"  Tool 執行: {'✅' if tool_worked else '❌'}")
        print(f"  耗時: {tool_time:.2f}s")

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
        print(f"簡單 prompt: {status} (回應: {RESULTS['simple_prompt']['response']})")
        all_pass = all_pass and RESULTS["simple_prompt"]["pass"]

    if RESULTS["tool_use"]:
        status = "✅ PASS" if RESULTS["tool_use"]["pass"] else "❌ FAIL"
        print(f"Tool use: {status}")
        all_pass = all_pass and RESULTS["tool_use"]["pass"]

    print(f"\nEvents:")
    for event, triggered in RESULTS["events"].items():
        print(f"  {event}: {'✅' if triggered else '❌'}")
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
