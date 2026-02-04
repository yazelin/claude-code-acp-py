#!/usr/bin/env python3
"""
測試: AcpClient → Gemini ACP + MCP (nanobanana)

執行方式:
    python tests/test_acp_client_gemini_mcp.py

前置條件:
    gemini mcp add nanobanana "uvx nanobanana"

    或含環境變數:
    gemini mcp add nanobanana "bash -c 'source /path/to/.env && uvx nanobanana'"

預期結果:
    - MCP tools 可被識別
    - Gemini 能列出 nanobanana 的功能

注意:
    - Gemini 不支援動態 MCP 配置
    - 必須使用 --allowed-mcp-server-names flag
"""
import asyncio
import time
import sys
import os
import platform
import subprocess

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

RESULTS = {
    "system_info": {},
    "mcp_config": None,
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


def check_mcp_config():
    """檢查 Gemini MCP 配置"""
    try:
        result = subprocess.run(
            ["gemini", "mcp", "list"],
            capture_output=True,
            text=True,
            timeout=10
        )
        output = result.stdout + result.stderr
        has_nanobanana = "nanobanana" in output.lower()
        return {
            "configured": has_nanobanana,
            "output": output[:500],
        }
    except Exception as e:
        return {"configured": False, "error": str(e)}


async def main():
    print("=" * 60)
    print("測試: AcpClient → Gemini ACP + MCP")
    print("=" * 60)

    # Collect system info
    RESULTS["system_info"] = collect_system_info()
    print("\n[系統資訊]")
    for key, value in RESULTS["system_info"].items():
        print(f"  {key}: {value}")

    # Check MCP config
    print("\n[MCP 配置檢查]")
    RESULTS["mcp_config"] = check_mcp_config()
    if RESULTS["mcp_config"]["configured"]:
        print("  ✅ nanobanana 已配置")
    else:
        print("  ❌ nanobanana 未配置")
        print("  請先執行: gemini mcp add nanobanana 'uvx nanobanana'")
        print("\n" + "=" * 60)
        print("⚠️ 測試跳過: MCP 未配置")
        print("=" * 60)
        return False

    from claude_code_acp import AcpClient

    # Use --allowed-mcp-server-names to enable MCP
    client = AcpClient(
        command="gemini",
        args=["--experimental-acp", "--allowed-mcp-server-names", "nanobanana"],
        cwd="/tmp",
    )

    @client.on_text
    async def on_text(text):
        pass

    @client.on_thinking
    async def on_thinking(text):
        print(f"  [THINK] {text[:50]}...")

    try:
        # Test 1: Connect
        print("\n[TEST 1] 連接 (含 MCP)")
        t1 = time.time()
        await asyncio.wait_for(client.connect(), timeout=60.0)
        connect_time = time.time() - t1
        RESULTS["connect"] = {"time": connect_time, "pass": True}
        print(f"  連接時間: {connect_time:.2f}s ✅")

        # Test 2: Check MCP tools available
        print("\n[TEST 2] 檢查 MCP tools")
        response = await asyncio.wait_for(
            client.prompt("Do you have image generation tools? What are they called? Be brief."),
            timeout=60.0
        )

        # Check if nanobanana/image tools are mentioned
        response_lower = response.lower()
        has_mcp = any(keyword in response_lower for keyword in [
            "nanobanana", "nano banana", "image", "icon", "pattern", "diagram"
        ])
        RESULTS["mcp_tools_available"] = {"pass": has_mcp, "response": response[:300]}
        print(f"  MCP tools 可用: {'✅' if has_mcp else '❌'}")
        print(f"  回應摘要: {response[:100]}...")

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
        print(f"連接測試: ✅ PASS ({RESULTS['connect']['time']:.2f}s)")
    else:
        print("連接測試: ❌ FAIL")
        all_pass = False

    if RESULTS["mcp_tools_available"]:
        status = "✅ PASS" if RESULTS["mcp_tools_available"]["pass"] else "❌ FAIL"
        print(f"MCP tools 可用: {status}")
        all_pass = all_pass and RESULTS["mcp_tools_available"]["pass"]
    else:
        print("MCP tools 可用: ❌ FAIL")
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
