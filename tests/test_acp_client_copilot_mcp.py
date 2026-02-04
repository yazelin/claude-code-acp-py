#!/usr/bin/env python3
"""
測試: AcpClient → Copilot CLI ACP Server + MCP

執行方式:
    python tests/test_acp_client_copilot_mcp.py

前置條件:
    - 安裝 GitHub Copilot CLI
    - 已登入 GitHub (gh auth login)
    - 設定 NANOBANANA_GEMINI_API_KEY 環境變數

預期結果:
    - 連接成功
    - MCP tools 可用

注意:
    - Copilot CLI 支援 --additional-mcp-config 動態 MCP 配置
"""
import asyncio
import json
import time
import sys
import os
import platform
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

RESULTS = {
    "system_info": {},
    "copilot_check": None,
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
            return {"available": True, "path": copilot_path}
        else:
            return {"available": False, "error": result.stderr}
    except Exception as e:
        return {"available": False, "error": str(e)}


async def main():
    print("=" * 60)
    print("測試: AcpClient → Copilot CLI ACP Server + MCP")
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
    else:
        print(f"  ❌ Copilot CLI 不可用: {RESULTS['copilot_check'].get('error')}")
        print("\n" + "=" * 60)
        print("⚠️ 測試跳過: Copilot CLI 未安裝")
        print("=" * 60)
        return False

    # Check API key
    print("\n[API Key 檢查]")
    api_key = os.environ.get("NANOBANANA_GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if api_key:
        print(f"  ✅ API Key 已設定 ({api_key[:8]}...)")
        RESULTS["api_key_check"] = True
    else:
        print("  ⚠️ API Key 未設定 (MCP 可能無法正常工作)")
        print("  設定方式: export NANOBANANA_GEMINI_API_KEY=your-key")
        RESULTS["api_key_check"] = False

    from claude_code_acp import AcpClient
    import tempfile

    # Copilot CLI uses --additional-mcp-config for dynamic MCP configuration
    # Format: {"mcpServers": {"name": {...}}}
    # Note: Copilot requires "type": "local" and "tools" field
    # Write config to a temp file (more reliable than JSON string on command line)
    mcp_config = {
        "mcpServers": {
            "nanobanana": {
                "type": "local",
                "command": "uvx",
                "args": ["nanobanana-py"],
                "tools": ["*"],  # Required by Copilot
                "env": {
                    # Copilot uses ${VAR} syntax for env expansion
                    "NANOBANANA_GEMINI_API_KEY": "${NANOBANANA_GEMINI_API_KEY}",
                },
            }
        }
    }

    # Create temp config file
    config_file = tempfile.NamedTemporaryFile(
        mode='w', suffix='.json', delete=False, prefix='copilot-mcp-'
    )
    json.dump(mcp_config, config_file)
    config_file.close()
    print(f"  MCP config file: {config_file.name}")

    client = AcpClient(
        command="copilot",
        args=[
            "--acp",
            "--additional-mcp-config", f"@{config_file.name}",
        ],
        cwd="/tmp",
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
        # Test 1: Connect with MCP (Copilot + MCP may take longer to initialize)
        print("\n[TEST 1] 連接 (含 MCP 配置)")
        t1 = time.time()
        await asyncio.wait_for(client.connect(), timeout=60.0)
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
            "nanobanana", "generate_image", "image", "icon", "pattern", "diagram"
        ])
        # Make sure it's not a "no" response
        is_negative = any(neg in response_lower for neg in [
            "don't have", "do not have", "no image", "not available", "i don't"
        ])
        has_mcp = has_mcp and not is_negative

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
    finally:
        # Clean up temp file
        try:
            os.unlink(config_file.name)
        except:
            pass

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
        print(f"MCP tools 可用: {status}")
    else:
        print("MCP tools 可用: ❌ FAIL")

    connect_result = RESULTS.get("connect") or {}
    mcp_result = RESULTS.get("mcp_tools_available") or {}
    all_pass = (
        connect_result.get("pass", False) and
        mcp_result.get("pass", False)
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
