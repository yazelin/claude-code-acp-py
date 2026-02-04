#!/usr/bin/env python3
"""
測試: AcpClient → claude-code-acp + MCP (動態配置)

執行方式:
    python tests/test_acp_client_claude_mcp.py

前置條件:
    需要設定 GEMINI_API_KEY 環境變數 (nanobanana 需要)

預期結果:
    - 動態 MCP 配置成功載入
    - MCP tools 可被識別

注意:
    - claude-code-acp 支援動態 MCP 配置 (與 Gemini 不同)
"""
import asyncio
import time
import sys
import os
import platform

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

RESULTS = {
    "system_info": {},
    "api_key_check": None,
    "connect": None,
    "mcp_tools_available": None,
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

    return info


async def main():
    print("=" * 60)
    print("測試: AcpClient → claude-code-acp + MCP (動態配置)")
    print("=" * 60)

    # Collect system info
    RESULTS["system_info"] = collect_system_info()
    print("\n[系統資訊]")
    for key, value in RESULTS["system_info"].items():
        print(f"  {key}: {value}")

    # Check API key
    print("\n[API Key 檢查]")
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("NANOBANANA_GEMINI_API_KEY")
    if api_key:
        print(f"  ✅ API Key 已設定 ({api_key[:8]}...)")
        RESULTS["api_key_check"] = True
    else:
        print("  ⚠️ API Key 未設定 (MCP 可能無法正常工作)")
        print("  設定方式: export GEMINI_API_KEY=your-key")
        RESULTS["api_key_check"] = False
        # Continue anyway to test if MCP config is passed

    from claude_code_acp import AcpClient

    # Dynamic MCP configuration (claude-code-acp supports this!)
    mcp_config = [{
        "name": "nanobanana",
        "command": "uvx",
        "args": ["nanobanana"],
        "env": {"GEMINI_API_KEY": api_key or ""},
    }]

    client = AcpClient(
        command="claude-code-acp",
        cwd="/tmp",
        mcp_servers=mcp_config,  # Dynamic MCP config!
    )

    @client.on_text
    async def on_text(text):
        pass

    @client.on_thinking
    async def on_thinking(text):
        print(f"  [THINK] {text[:50]}...")

    @client.on_tool_start
    async def on_tool_start(tool_id, name, input_data):
        print(f"  [TOOL] {name}")

    @client.on_permission
    async def on_permission(name, input_data, options):
        return "allow"

    try:
        # Test 1: Connect with MCP
        print("\n[TEST 1] 連接 (含動態 MCP 配置)")
        t1 = time.time()
        await asyncio.wait_for(client.connect(), timeout=30.0)
        connect_time = time.time() - t1
        RESULTS["connect"] = {"time": connect_time, "pass": True}
        print(f"  連接時間: {connect_time:.2f}s ✅")

        # Test 2: Check MCP tools
        print("\n[TEST 2] 檢查 MCP tools 是否可用")
        response = await asyncio.wait_for(
            client.prompt("Do you have any image generation tools available? List their names briefly."),
            timeout=60.0
        )

        response_lower = response.lower()
        has_mcp = any(keyword in response_lower for keyword in [
            "nanobanana", "generate_image", "image", "icon", "pattern"
        ])
        RESULTS["mcp_tools_available"] = {"pass": has_mcp, "response": response[:300]}
        print(f"  MCP tools 可用: {'✅' if has_mcp else '❌'}")
        print(f"  回應: {response[:150]}...")

        await client.disconnect()

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

    if RESULTS["mcp_tools_available"]:
        status = "✅ PASS" if RESULTS["mcp_tools_available"]["pass"] else "❌ FAIL"
        print(f"動態 MCP 配置: {status}")
    else:
        print("動態 MCP 配置: ❌ FAIL")

    all_pass = (
        RESULTS.get("connect", {}).get("pass", False) and
        RESULTS.get("mcp_tools_available", {}).get("pass", False)
    )

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
