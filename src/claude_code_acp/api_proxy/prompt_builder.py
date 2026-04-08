"""
OpenAI Chat Completions ↔ flat-prompt adapter.

Ported from yazelin/gemini-web's openclaw_adapter.py and adapted from
Gemini API contents format to OpenAI Chat Completions messages format.

Design (inherited from gemini-web):
- Completely stateless. Every request flattens the full conversation
  history into one prompt; nothing is remembered between calls.
- Tool calling is implemented via prompt engineering (TOOL PROTOCOL block),
  not via the backend's native tool support, so it works with any backend
  that just takes a string prompt and returns text.
- The model is told to either return plain text OR a single-line JSON
  {"tool_call": {"name": ..., "args": ...}}. We parse the response with
  three layers of fallback (legacy text marker, json.loads, regex rescue).
- A whitelist of allowed tool names is enforced as a second line of
  defense against the model calling tools that don't actually exist.
"""

from __future__ import annotations

import json
import re
from typing import Any


# ── Tool schema 格式化 ──────────────────────────────────────────────


def _format_tool_schema(func: dict[str, Any]) -> str:
    """把單一 OpenAI function 工具格式化成可讀的文字描述。"""
    name = func.get("name", "<unknown>")
    desc = (func.get("description") or "").strip()
    params = func.get("parameters") or {}
    props = params.get("properties") or {}
    required = set(params.get("required") or [])

    arg_lines = []
    for arg_name, arg_schema in props.items():
        if not isinstance(arg_schema, dict):
            continue
        arg_type = arg_schema.get("type", "any")
        arg_desc = (arg_schema.get("description") or "").strip()
        marker = "" if arg_name in required else "?"
        line = f"    - {arg_name}{marker} ({arg_type})"
        if arg_desc:
            line += f": {arg_desc}"
        arg_lines.append(line)

    block = [f"- {name}"]
    if desc:
        block.append(f"  description: {desc}")
    if arg_lines:
        block.append("  arguments:")
        block.extend(arg_lines)
    else:
        block.append("  arguments: (none)")
    return "\n".join(block)


def _extract_function_decls(tools: list[Any] | None) -> list[dict[str, Any]]:
    """從 OpenAI tools 陣列裡撈出所有 function 定義。

    OpenAI 格式: [{"type": "function", "function": {"name": ..., "description": ..., "parameters": ...}}]
    """
    decls: list[dict[str, Any]] = []
    for tool in tools or []:
        if not isinstance(tool, dict):
            continue
        if tool.get("type") != "function":
            continue
        func = tool.get("function")
        if isinstance(func, dict) and func.get("name"):
            decls.append(func)
    return decls


# ── 訊息歷史攤平 ──────────────────────────────────────────────────────


def _content_to_text(content: Any) -> str:
    """把 OpenAI message content 轉成純文字。

    content 可以是 str,也可以是 list[dict]。"""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                t = item.get("type")
                if t == "text":
                    parts.append(str(item.get("text", "")))
                elif t == "image_url":
                    url = (item.get("image_url") or {}).get("url", "")
                    parts.append(f"[image: {url[:80]}]")
                else:
                    parts.append(f"[{t or 'unknown'}]")
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(p for p in parts if p)
    return str(content)


def _format_tool_call(tc: dict[str, Any]) -> str:
    """把過往的 assistant tool_call 序列化成 PAST_TOOL_INVOCATION 標籤。

    用 PAST_TOOL_INVOCATION (而非 [tool_call]) 是為了避免模型看歷史時誤
    以為這是「合法的呼叫格式」並去模仿 — 那會破壞 TOOL PROTOCOL 的單行
    JSON 規範。
    """
    func = tc.get("function") or {}
    name = func.get("name", "<unknown>")
    args_raw = func.get("arguments", "")
    # OpenAI tool_calls 的 arguments 是一個 JSON 字串(不是 dict)
    if isinstance(args_raw, str):
        try:
            args_obj = json.loads(args_raw) if args_raw else {}
        except (json.JSONDecodeError, ValueError):
            args_obj = {"_raw": args_raw}
    else:
        args_obj = args_raw or {}
    try:
        args_json = json.dumps(args_obj, ensure_ascii=False)
    except (TypeError, ValueError):
        args_json = str(args_obj)
    return f"<PAST_TOOL_INVOCATION name={name}>{args_json}</PAST_TOOL_INVOCATION>"


def _format_tool_result(name: str, content: Any) -> str:
    """把 OpenAI 'tool' role 訊息序列化成 PAST_TOOL_RESULT 標籤。"""
    if isinstance(content, (dict, list)):
        try:
            body = json.dumps(content, ensure_ascii=False)
        except (TypeError, ValueError):
            body = str(content)
    else:
        body = str(content if content is not None else "")
    return f"<PAST_TOOL_RESULT name={name}>{body}</PAST_TOOL_RESULT>"


def _flatten_messages(
    messages: list[dict[str, Any]],
) -> tuple[str, str]:
    """把 OpenAI messages 陣列攤平成 (system_text, conversation_text)。

    Returns:
        (system_text, history_text)
        - system_text: 所有 'system' role 訊息合併
        - history_text: 其他訊息 (user / assistant / tool) 依序串成多段對話

    被攤平的歷史會用 "User: ...\\n\\nAssistant: ..." 這種格式呈現,
    過去的 tool 呼叫和結果用 PAST_TOOL_INVOCATION / PAST_TOOL_RESULT 包裝。
    """
    system_parts: list[str] = []
    history_lines: list[str] = []

    # 為了串對應 tool_call_id → name 的關係(OpenAI 'tool' role 訊息只有 id,沒有 name),
    # 先掃一遍 assistant tool_calls 把 id→name 記下來
    tool_id_to_name: dict[str, str] = {}
    for msg in messages or []:
        if not isinstance(msg, dict):
            continue
        if msg.get("role") == "assistant":
            for tc in msg.get("tool_calls") or []:
                if isinstance(tc, dict):
                    tc_id = tc.get("id", "")
                    name = ((tc.get("function") or {}).get("name", "")) or ""
                    if tc_id and name:
                        tool_id_to_name[tc_id] = name

    for msg in messages or []:
        if not isinstance(msg, dict):
            continue
        role = msg.get("role", "")

        if role == "system":
            text = _content_to_text(msg.get("content"))
            if text.strip():
                system_parts.append(text.strip())
            continue

        if role == "user":
            text = _content_to_text(msg.get("content"))
            if text:
                history_lines.append(f"User: {text}")
            continue

        if role == "assistant":
            chunks: list[str] = []
            text = _content_to_text(msg.get("content"))
            if text:
                chunks.append(text)
            for tc in msg.get("tool_calls") or []:
                if isinstance(tc, dict):
                    chunks.append(_format_tool_call(tc))
            if chunks:
                history_lines.append("Assistant: " + "\n".join(chunks))
            continue

        if role == "tool":
            tc_id = msg.get("tool_call_id", "")
            name = msg.get("name") or tool_id_to_name.get(tc_id, "<unknown>")
            text = _content_to_text(msg.get("content"))
            history_lines.append(f"Tool: {_format_tool_result(name, text)}")
            continue

        # 未知 role,當 user 處理
        text = _content_to_text(msg.get("content"))
        if text:
            history_lines.append(f"{role.capitalize() or 'User'}: {text}")

    system_text = "\n\n".join(system_parts).strip()
    history_text = "\n\n".join(history_lines).strip()
    return system_text, history_text


# ── Tool call prompt 模板 ─────────────────────────────────────────────


_TOOL_CALL_INSTRUCTION = """\
[TOOL PROTOCOL — READ CAREFULLY]

You are running inside a custom agent runtime. The following tools — and ONLY these tools — are available to you:

{tool_schemas}

Allowed tool names (exact match required): {tool_names}

CRITICAL RULES:
1. You MUST NOT call any built-in tools (e.g. Read, Write, Bash, Glob, Grep, Edit). They do not exist in this runtime and will fail.
2. If you want to call a tool, you MUST use one of the names in the allowed list above, with the exact spelling.
3. To call a tool, your ENTIRE response must be a single JSON object on one line, no markdown, no code fences, no prose before or after:
   {{"tool_call": {{"name": "<one_of_the_allowed_names>", "args": {{<arguments_matching_the_schema>}}}}}}
4. If you do NOT need any tool, respond in plain natural language as usual.
5. Choose EXACTLY ONE: either output the tool_call JSON object, or output plain text. Never both.
6. If the user's request requires capabilities not covered by the allowed tools, respond in plain text explaining what you would need.
"""


def build_prompt(body: dict[str, Any]) -> tuple[str, bool, set[str]]:
    """
    把 OpenAI Chat Completions 的 request body 組成一段給 backend 的 prompt。

    Returns:
        (prompt_text, has_function_tools, allowed_tool_names)
        - has_function_tools: 是否注入了 TOOL PROTOCOL
        - allowed_tool_names: 宣告的工具名稱集合 (用於後續驗證解析出來的 tool call)
    """
    messages = body.get("messages") or []
    func_decls = _extract_function_decls(body.get("tools"))

    system_text, history_text = _flatten_messages(messages)

    sections: list[str] = []

    if system_text:
        sections.append(f"[System Instruction]\n{system_text}")

    has_func_tools = bool(func_decls)
    allowed_names: set[str] = {fd["name"] for fd in func_decls if fd.get("name")}
    if has_func_tools:
        tool_schemas = "\n\n".join(_format_tool_schema(fd) for fd in func_decls)
        tool_names_str = ", ".join(f"`{n}`" for n in sorted(allowed_names))
        sections.append(
            _TOOL_CALL_INSTRUCTION.format(tool_schemas=tool_schemas, tool_names=tool_names_str)
        )

    if history_text:
        sections.append(f"[Conversation]\n{history_text}")

    sections.append("Assistant:")
    return "\n\n".join(sections), has_func_tools, allowed_names


# ── 回應解析 (text → tool_call) ─────────────────────────────────────


def _strip_code_fence(text: str) -> str:
    """去掉 ```json ... ``` 或 ``` ... ``` 包裹。"""
    text = text.strip()
    m = re.search(r"```(?:json|JSON)?\s*([\s\S]*?)\s*```", text)
    if m:
        return m.group(1).strip()
    return text


def _try_extract_json_object(text: str) -> dict[str, Any] | None:
    """從文字裡盡量擷取一個合法的 JSON object。多策略容錯。"""
    cleaned = _strip_code_fence(text)

    # 策略 1: 整段直接 parse
    try:
        obj = json.loads(cleaned)
        if isinstance(obj, dict):
            return obj
    except (json.JSONDecodeError, ValueError):
        pass

    # 策略 2: 抓第一對 balanced 大括號 (簡單版,不處理字串中的 brace)
    start = cleaned.find("{")
    if start == -1:
        return None
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(cleaned)):
        ch = cleaned[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                candidate = cleaned[start : i + 1]
                try:
                    obj = json.loads(candidate)
                    if isinstance(obj, dict):
                        return obj
                except (json.JSONDecodeError, ValueError):
                    break
    return None


# 用 regex rescue parser:模型有時輸出未 escape 引號的「假 JSON」,
# 例如 {"args": {"command": "grep -oP "regex""}}。
# 我們假設外層 envelope 為 {"tool_call":{"name":"X","args":{...}}},直接抓 key/value。
_LEGACY_TOOL_CALL = re.compile(
    r"\[tool_call\]\s*([A-Za-z_][A-Za-z0-9_-]*)\s*\((\{.*\})\s*\)\s*$",
    re.DOTALL,
)
_RESCUE_NAME = re.compile(r'"name"\s*:\s*"([A-Za-z_][A-Za-z0-9_-]*)"')
_RESCUE_ARGS_OPEN = re.compile(r'"args"\s*:\s*\{')
_RESCUE_ARG_KEY = re.compile(r'(?:^|,)\s*"([A-Za-z_][A-Za-z0-9_-]*)"\s*:\s*')


def _rescue_parse_tool_call(text: str) -> dict[str, Any] | None:
    """JSON parse 失敗時的 rescue 邏輯。

    處理模型輸出未 escape 引號的「假 JSON」,例如:
        {"tool_call": {"name": "exec", "args": {
            "command": "bash foo.sh --prompt "a red apple"",
            "timeout": 180
        }}}
    用 regex 結構性地切出 name 跟每個 arg 的 key/value。
    """
    cleaned = _strip_code_fence(text).strip()
    if "tool_call" not in cleaned and '"name"' not in cleaned:
        return None

    name_match = _RESCUE_NAME.search(cleaned)
    if not name_match:
        return None
    name = name_match.group(1)

    args_open = _RESCUE_ARGS_OPEN.search(cleaned)
    if not args_open:
        return None
    args_start = args_open.end()

    end_match = re.search(r"\}\s*\}\s*\}\s*$", cleaned)
    if not end_match:
        return None
    args_end = end_match.start()
    if args_end <= args_start:
        return None

    args_body = cleaned[args_start:args_end]
    key_matches = list(_RESCUE_ARG_KEY.finditer(args_body))
    if not key_matches:
        return None

    args: dict[str, Any] = {}
    for i, m in enumerate(key_matches):
        key = m.group(1)
        value_start = m.end()
        value_end = key_matches[i + 1].start() if i + 1 < len(key_matches) else len(args_body)
        raw_value = args_body[value_start:value_end].rstrip(", \t\n\r")

        if not raw_value:
            continue

        if raw_value.startswith('"'):
            inner = raw_value[1:]
            if inner.endswith('"'):
                inner = inner[:-1]
            else:
                last_q = inner.rfind('"')
                if last_q >= 0:
                    inner = inner[:last_q]
            args[key] = inner
        else:
            try:
                args[key] = json.loads(raw_value)
            except (json.JSONDecodeError, ValueError):
                args[key] = raw_value

    if not args:
        return None

    return {"tool_call": {"name": name, "args": args}}


def parse_tool_call(
    text: str,
    allowed_names: set[str] | None = None,
) -> dict[str, Any] | None:
    """嘗試把 backend 回應的純文字解析成 tool call。

    支援的格式:
        {"tool_call": {"name": "...", "args": {...}}}
        {"name": "...", "args": {...}}        # 寬鬆 fallback
        {"name": "...", "arguments": {...}}   # 寬鬆 fallback
        [tool_call] name({json})              # legacy 文字標記

    Returns:
        {"name": str, "args": dict}  或 None (解析失敗、不是 tool call、或名稱不在白名單)
    """
    if not text or not text.strip():
        return None

    legacy = _LEGACY_TOOL_CALL.search(text.strip())
    if legacy:
        name = legacy.group(1)
        args_text = legacy.group(2)
        try:
            args_obj = json.loads(args_text)
            if isinstance(args_obj, dict):
                obj: dict[str, Any] | None = {"tool_call": {"name": name, "args": args_obj}}
            else:
                obj = None
        except (json.JSONDecodeError, ValueError):
            obj = None
    else:
        obj = None

    if obj is None:
        obj = _try_extract_json_object(text)
    if obj is None:
        obj = _rescue_parse_tool_call(text)
    if obj is None:
        return None

    candidate: dict[str, Any] | None = None

    if "tool_call" in obj and isinstance(obj["tool_call"], dict):
        tc = obj["tool_call"]
        name = tc.get("name")
        args = tc.get("args") or tc.get("arguments") or {}
        if isinstance(name, str) and name:
            candidate = {"name": name, "args": args if isinstance(args, dict) else {}}

    if candidate is None and "name" in obj and isinstance(obj["name"], str):
        if "args" in obj or "arguments" in obj:
            args = obj.get("args") or obj.get("arguments") or {}
            candidate = {
                "name": obj["name"],
                "args": args if isinstance(args, dict) else {},
            }

    if candidate is None:
        return None

    if allowed_names is not None and candidate["name"] not in allowed_names:
        return None

    return candidate


def build_response_parts(
    text: str,
    has_function_tools: bool,
    allowed_tool_names: set[str] | None = None,
) -> tuple[str | None, list[dict[str, Any]] | None, str]:
    """把 backend 純文字回應包成 OpenAI assistant message 的 (content, tool_calls, finish_reason)。

    Args:
        text: backend 純文字回應
        has_function_tools: 本次請求是否注入了 TOOL PROTOCOL
        allowed_tool_names: 宣告的工具名稱集合,用於驗證 tool call name

    Returns:
        (content, tool_calls, finish_reason)
        - 純文字回應: (text, None, "stop")
        - 工具呼叫:   (None, [{id, type:"function", function:{name, arguments}}], "tool_calls")
    """
    if has_function_tools:
        tc = parse_tool_call(text, allowed_names=allowed_tool_names)
        if tc is not None:
            try:
                args_json = json.dumps(tc["args"], ensure_ascii=False)
            except (TypeError, ValueError):
                args_json = "{}"
            import uuid

            return (
                None,
                [
                    {
                        "id": f"call_{uuid.uuid4().hex[:16]}",
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": args_json,
                        },
                    }
                ],
                "tool_calls",
            )

    return (text or "", None, "stop")
