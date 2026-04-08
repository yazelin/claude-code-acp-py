"""CLI entry point for claude-acp-api.

Usage:
    claude-acp-api                            # default: claude backend, port 8788
    claude-acp-api --port 3456 --host 0.0.0.0
    claude-acp-api --backend claude --model opus
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

from .backends.claude import ClaudeBackend
from .server import create_app


def setup_logging(level_name: str) -> None:
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="claude-acp-api",
        description="OpenAI-compatible HTTP API server backed by Claude CLI / ACP",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("CLAUDE_ACP_API_HOST", "127.0.0.1"),
        help="bind host (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("CLAUDE_ACP_API_PORT", "8788")),
        help="bind port (default: 8788)",
    )
    parser.add_argument(
        "--backend",
        default=os.environ.get("CLAUDE_ACP_API_BACKEND", "claude"),
        choices=["claude"],
        help="backend implementation (default: claude)",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("CLAUDE_ACP_API_MODEL"),
        help="default model alias passed to backend (e.g. opus / sonnet / haiku)",
    )
    parser.add_argument(
        "--log-level",
        default=os.environ.get("CLAUDE_ACP_API_LOG_LEVEL", "info"),
        choices=["debug", "info", "warning", "error", "critical"],
    )

    args = parser.parse_args()
    setup_logging(args.log_level)

    logger = logging.getLogger("claude_code_acp.api_proxy")

    if args.backend == "claude":
        backend = ClaudeBackend(model=args.model)
    else:
        parser.error(f"unknown backend: {args.backend}")
        return  # unreachable

    app = create_app(backend)

    try:
        import uvicorn
    except ImportError:
        logger.error(
            "uvicorn is required. Install with: pip install 'claude-code-acp[api-proxy]'"
        )
        sys.exit(1)

    logger.info(
        "starting claude-acp-api on http://%s:%d (backend=%s)",
        args.host,
        args.port,
        args.backend,
    )
    uvicorn.run(app, host=args.host, port=args.port, log_level=args.log_level)


if __name__ == "__main__":
    main()
