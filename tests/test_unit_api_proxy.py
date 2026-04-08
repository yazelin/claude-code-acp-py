"""Unit tests for claude_code_acp.api_proxy — prompt_builder and parse logic.

These tests are fully offline (no subprocess, no network, no ACP).
"""

from __future__ import annotations

import json

import pytest

from claude_code_acp.api_proxy.prompt_builder import (
    build_prompt,
    build_response_parts,
    parse_tool_call,
)


# ── build_prompt ────────────────────────────────────────────────────────────


class TestBuildPrompt:
    def _simple_body(self, user_text: str = "Hello") -> dict:
        return {"messages": [{"role": "user", "content": user_text}]}

    def test_returns_tuple(self):
        prompt, has_tools, names = build_prompt(self._simple_body())
        assert isinstance(prompt, str)
        assert isinstance(has_tools, bool)
        assert isinstance(names, set)

    def test_no_tools(self):
        _, has_tools, names = build_prompt(self._simple_body())
        assert has_tools is False
        assert names == set()

    def test_prompt_ends_with_assistant_marker(self):
        prompt, _, _ = build_prompt(self._simple_body())
        assert prompt.endswith("Assistant:")

    def test_user_message_included(self):
        prompt, _, _ = build_prompt(self._simple_body("Tell me a joke"))
        assert "Tell me a joke" in prompt

    def test_system_message_included(self):
        body = {
            "messages": [
                {"role": "system", "content": "You are a pirate."},
                {"role": "user", "content": "Hi"},
            ]
        }
        prompt, _, _ = build_prompt(body)
        assert "You are a pirate." in prompt
        assert "[System Instruction]" in prompt

    def test_with_function_tools(self):
        body = {
            "messages": [{"role": "user", "content": "Run ls"}],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "exec",
                        "description": "Run a shell command",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "command": {"type": "string", "description": "The shell command"},
                            },
                            "required": ["command"],
                        },
                    },
                }
            ],
        }
        prompt, has_tools, names = build_prompt(body)
        assert has_tools is True
        assert "exec" in names
        assert "TOOL PROTOCOL" in prompt
        assert "exec" in prompt

    def test_multiple_turns_flattened(self):
        body = {
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"},
                {"role": "user", "content": "How are you?"},
            ]
        }
        prompt, _, _ = build_prompt(body)
        assert "Hello" in prompt
        assert "Hi there!" in prompt
        assert "How are you?" in prompt

    def test_tool_result_in_history(self):
        body = {
            "messages": [
                {"role": "user", "content": "Run ls"},
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_abc",
                            "type": "function",
                            "function": {"name": "exec", "arguments": '{"command":"ls"}'},
                        }
                    ],
                },
                {
                    "role": "tool",
                    "tool_call_id": "call_abc",
                    "content": "file1.txt\nfile2.txt",
                },
            ]
        }
        prompt, _, _ = build_prompt(body)
        assert "PAST_TOOL_INVOCATION" in prompt
        assert "PAST_TOOL_RESULT" in prompt
        assert "file1.txt" in prompt

    def test_empty_messages_list(self):
        """Empty messages should still return a valid tuple."""
        prompt, has_tools, names = build_prompt({"messages": []})
        assert isinstance(prompt, str)
        assert has_tools is False


# ── parse_tool_call ──────────────────────────────────────────────────────────


class TestParseToolCall:
    def test_parses_standard_format(self):
        text = '{"tool_call": {"name": "exec", "args": {"command": "ls"}}}'
        result = parse_tool_call(text, allowed_names={"exec"})
        assert result is not None
        assert result["name"] == "exec"
        assert result["args"] == {"command": "ls"}

    def test_parses_loose_format_without_tool_call_wrapper(self):
        text = '{"name": "exec", "args": {"command": "ls"}}'
        result = parse_tool_call(text, allowed_names={"exec"})
        assert result is not None
        assert result["name"] == "exec"

    def test_parses_arguments_alias(self):
        text = '{"name": "exec", "arguments": {"command": "ls"}}'
        result = parse_tool_call(text, allowed_names={"exec"})
        assert result is not None
        assert result["args"] == {"command": "ls"}

    def test_rejects_disallowed_tool_name(self):
        text = '{"tool_call": {"name": "hack", "args": {}}}'
        result = parse_tool_call(text, allowed_names={"exec"})
        assert result is None

    def test_passes_through_when_no_whitelist(self):
        text = '{"tool_call": {"name": "anything", "args": {}}}'
        result = parse_tool_call(text, allowed_names=None)
        assert result is not None
        assert result["name"] == "anything"

    def test_returns_none_for_plain_text(self):
        result = parse_tool_call("Just a plain text response.", allowed_names={"exec"})
        assert result is None

    def test_returns_none_for_empty_string(self):
        assert parse_tool_call("", allowed_names={"exec"}) is None
        assert parse_tool_call("   ", allowed_names={"exec"}) is None

    def test_handles_code_fence_wrapping(self):
        text = '```json\n{"tool_call": {"name": "exec", "args": {"command": "ls"}}}\n```'
        result = parse_tool_call(text, allowed_names={"exec"})
        assert result is not None
        assert result["name"] == "exec"

    def test_legacy_text_marker(self):
        text = '[tool_call] exec({"command": "ls"})'
        result = parse_tool_call(text, allowed_names={"exec"})
        assert result is not None
        assert result["name"] == "exec"
        assert result["args"] == {"command": "ls"}


# ── build_response_parts ─────────────────────────────────────────────────────


class TestBuildResponseParts:
    def test_plain_text_response(self):
        content, tool_calls, reason = build_response_parts(
            "Hello world", has_function_tools=False
        )
        assert content == "Hello world"
        assert tool_calls is None
        assert reason == "stop"

    def test_tool_call_response(self):
        text = '{"tool_call": {"name": "exec", "args": {"command": "ls"}}}'
        content, tool_calls, reason = build_response_parts(
            text, has_function_tools=True, allowed_tool_names={"exec"}
        )
        assert content is None
        assert reason == "tool_calls"
        assert tool_calls is not None
        assert len(tool_calls) == 1
        tc = tool_calls[0]
        assert tc["type"] == "function"
        assert tc["function"]["name"] == "exec"
        # arguments must be a valid JSON string
        args = json.loads(tc["function"]["arguments"])
        assert args == {"command": "ls"}

    def test_tool_call_id_format(self):
        text = '{"tool_call": {"name": "exec", "args": {}}}'
        _, tool_calls, _ = build_response_parts(
            text, has_function_tools=True, allowed_tool_names={"exec"}
        )
        assert tool_calls[0]["id"].startswith("call_")

    def test_no_tools_even_if_json_looks_like_tool_call(self):
        """When has_function_tools=False, never parse tool calls."""
        text = '{"tool_call": {"name": "exec", "args": {}}}'
        content, tool_calls, reason = build_response_parts(
            text, has_function_tools=False
        )
        assert content == text
        assert tool_calls is None
        assert reason == "stop"

    def test_disallowed_tool_falls_back_to_text(self):
        text = '{"tool_call": {"name": "unauthorized", "args": {}}}'
        content, tool_calls, reason = build_response_parts(
            text, has_function_tools=True, allowed_tool_names={"exec"}
        )
        # name not in whitelist → treat as plain text
        assert tool_calls is None
        assert reason == "stop"
        assert content == text
