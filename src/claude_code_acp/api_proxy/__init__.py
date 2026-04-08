"""
OpenAI-compatible HTTP API proxy backed by ACP / Claude SDK.

This module exposes an OpenAI Chat Completions endpoint at /v1/chat/completions
that internally drives a Claude (or any ACP) backend through prompt
engineering for tool calling. It is the Python sibling of `claude-max-api-proxy`
but with first-class tool calling support (via the `gemini-web` style protocol)
and pluggable backends.

Use case: let any OpenAI-compatible client (OpenClaw, opencode, cline, etc.)
talk to the Claude CLI under your Claude Max subscription, or to any other
ACP backend (Gemini CLI, custom agents) without paying per-token API fees.

Optional dependency group: pip install claude-code-acp[api-proxy]
"""

from .prompt_builder import build_prompt, parse_tool_call, build_response_parts

__all__ = [
    "build_prompt",
    "parse_tool_call",
    "build_response_parts",
]
