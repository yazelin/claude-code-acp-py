"""FastAPI server exposing OpenAI-compatible /v1/chat/completions.

The server is intentionally minimal:
- /health         — liveness probe
- /v1/models      — list available model aliases for the chosen backend
- /v1/chat/completions — non-streaming OpenAI Chat Completions endpoint

Streaming (SSE) is not implemented in MVP. Clients that ask for stream=true
get a single-shot response (which most OpenAI clients accept gracefully).
"""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any

from .backends.base import Backend
from .prompt_builder import build_prompt, build_response_parts

logger = logging.getLogger(__name__)

# fastapi is an optional dependency; importing here at module level (rather than
# inside create_app) is necessary so that type annotations on route handlers
# resolve correctly during route registration.
try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import JSONResponse
except ImportError:  # pragma: no cover
    FastAPI = None  # type: ignore[assignment,misc]
    HTTPException = None  # type: ignore[assignment,misc]
    Request = None  # type: ignore[assignment,misc]
    JSONResponse = None  # type: ignore[assignment,misc]


# Default model aliases exposed via /v1/models. The actual mapping to
# backend-specific names is left to the backend.
DEFAULT_MODELS = [
    {"id": "claude-opus-4", "alias": "opus"},
    {"id": "claude-sonnet-4", "alias": "sonnet"},
    {"id": "claude-haiku-4", "alias": "haiku"},
]


def create_app(backend: Backend):
    """Create the FastAPI application bound to a specific backend."""
    if FastAPI is None:
        raise RuntimeError(
            "fastapi is required. Install with: pip install 'claude-code-acp[api-proxy]'"
        )

    @asynccontextmanager
    async def lifespan(app):
        logger.info(f"api_proxy started (backend={backend.name})")
        yield
        await backend.close()
        logger.info("api_proxy stopped")

    app = FastAPI(
        title="claude-code-acp api_proxy",
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "backend": backend.name,
            "timestamp": int(time.time() * 1000),
        }

    @app.get("/v1/models")
    async def list_models() -> dict[str, Any]:
        return {
            "object": "list",
            "data": [
                {
                    "id": m["id"],
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": backend.name,
                }
                for m in DEFAULT_MODELS
            ],
        }

    @app.post("/v1/chat/completions")
    async def chat_completions(request: Request):
        try:
            body = await request.json()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"invalid JSON body: {e}") from e

        if not isinstance(body, dict):
            raise HTTPException(status_code=400, detail="body must be a JSON object")

        messages = body.get("messages")
        if not isinstance(messages, list) or not messages:
            raise HTTPException(status_code=400, detail="messages must be a non-empty list")

        model = body.get("model") or "claude-sonnet-4"

        # Build the flat prompt + tool protocol injection
        prompt, has_tools, allowed_names = build_prompt(body)

        logger.info(
            "chat.completions: model=%s, prompt=%d chars, turns=%d, tools=%d",
            model,
            len(prompt),
            len(messages),
            len(allowed_names),
        )

        try:
            text = await backend.query(prompt, model=_map_model(model))
        except Exception as e:
            logger.exception("backend query failed")
            raise HTTPException(status_code=502, detail=f"backend error: {e}") from e

        content, tool_calls, finish_reason = build_response_parts(
            text=text,
            has_function_tools=has_tools,
            allowed_tool_names=allowed_names,
        )

        message: dict[str, Any] = {"role": "assistant"}
        if tool_calls:
            message["content"] = None
            message["tool_calls"] = tool_calls
        else:
            message["content"] = content

        response = {
            "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": message,
                    "finish_reason": finish_reason,
                }
            ],
            "usage": {
                # We don't have real token counts from the CLI subprocess,
                # so we report zeros. Clients that rely on this field will
                # see no metering — that's an MVP limitation.
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            },
        }

        return JSONResponse(content=response)

    return app


# Mapping from OpenAI-style model name → backend-specific alias.
# The backend (ClaudeClient) accepts opus / sonnet / haiku.
_MODEL_MAP = {
    "claude-opus-4": "opus",
    "claude-sonnet-4": "sonnet",
    "claude-haiku-4": "haiku",
    "claude-opus-4-6": "opus",
    "claude-sonnet-4-5": "sonnet",
    "claude-sonnet-4-6": "sonnet",
    "claude-haiku-4-5": "haiku",
    "opus": "opus",
    "sonnet": "sonnet",
    "haiku": "haiku",
}


def _map_model(name: str) -> str:
    """Translate an OpenAI-style model name to a Claude CLI alias."""
    if not name:
        return "sonnet"
    if name in _MODEL_MAP:
        return _MODEL_MAP[name]
    # Strip any provider prefix like "anthropic/" or "claude-max-local/"
    if "/" in name:
        return _map_model(name.split("/", 1)[1])
    # Pass through anything else; the SDK will reject if invalid
    return name
