"""Claude backend powered by in-process ClaudeClient.

Each query spins up a fresh ClaudeClient with an isolated working directory
and tears it down when done. This matches the stateless design used by
ching-tech-os: every HTTP request is fully independent.

Permissions are denied for all built-in Claude tools (Read/Write/Bash/etc.)
because we want Claude to follow the TOOL PROTOCOL prompt and respond with
either text or our JSON tool_call format — not actually execute filesystem
or shell operations.

The system_prompt is set to a minimal override that breaks Claude Code's
default agentic preset, so the model behaves as a plain chat model that
follows the user-supplied TOOL PROTOCOL strictly.
"""

from __future__ import annotations

import logging
import shutil
import tempfile

from ...client import ClaudeClient

logger = logging.getLogger(__name__)


# Minimal system prompt that overrides Claude Code's default preset.
# This is critical: without it, Claude treats every request as an agentic
# coding task and ignores user-injected protocols like our TOOL PROTOCOL.
_DEFAULT_SYSTEM_PROMPT = (
    "You are an assistant integrated into a custom HTTP API gateway. "
    "Follow the user's prompt exactly as written. "
    "Do not assume you are Claude Code or any specific agent runtime. "
    "Do not attempt to read, write, or execute anything on the filesystem; "
    "all such operations must go through the protocol described in the user's prompt."
)


class ClaudeBackend:
    """In-process Claude backend using ClaudeClient.

    The Claude CLI subprocess is the only external process; everything
    else (ACP agent, prompt routing, response collection) runs inside
    this Python process.
    """

    name = "claude"

    def __init__(
        self,
        *,
        model: str | None = None,
        system_prompt: str | dict | None = None,
    ) -> None:
        """
        Args:
            model: Default model alias for Claude CLI (opus / sonnet / haiku).
                Can be overridden per query.
            system_prompt: Optional override for Claude's system prompt.
                If None, uses our minimal override that breaks Claude Code's
                agentic preset (so the model follows user-supplied protocols
                like the TOOL PROTOCOL strictly).
        """
        self._model = model
        self._system_prompt = (
            system_prompt if system_prompt is not None else _DEFAULT_SYSTEM_PROMPT
        )

    async def query(self, prompt: str, *, model: str | None = None) -> str:
        """Run one prompt through a fresh ClaudeClient and return the text."""
        # 為每個請求建立隔離的工作目錄,避免跨請求洩漏
        workdir = tempfile.mkdtemp(prefix="claude-acp-api-")
        try:
            client = ClaudeClient(
                cwd=workdir,
                system_prompt=self._system_prompt,
            )

            # Deny all tool uses — we don't want Claude actually running
            # filesystem/shell tools. The TOOL PROTOCOL in the prompt should
            # push Claude to respond with our JSON format instead.
            @client.on_permission
            async def _deny_all(name: str, raw_input: dict) -> bool:
                logger.debug(f"denied built-in tool: {name}")
                return False

            # 切到指定 model (如果有提供)
            effective_model = model or self._model
            try:
                async with client:
                    if effective_model:
                        try:
                            await client.set_model(effective_model)
                        except Exception as e:
                            logger.warning(f"set_model({effective_model}) failed: {e}")
                    text = await client.query(prompt)
                    logger.info(
                        "claude returned %d chars (first 300): %r",
                        len(text or ""),
                        (text or "")[:300],
                    )
                    return text or ""
            except Exception as e:
                logger.error(f"ClaudeClient query failed: {e}", exc_info=True)
                raise
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

    async def close(self) -> None:
        """No persistent resources to release (everything is per-request)."""
        return None
