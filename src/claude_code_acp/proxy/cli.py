#!/usr/bin/env python3
"""
CLI entry point for ACP Proxy.

This CLI accepts the same flags as Copilot CLI for compatibility,
allowing Copilot SDK to connect to it seamlessly.

Usage:
    copilot-acp-proxy --headless --stdio --backend gemini
    copilot-acp-proxy --headless --stdio --backend claude-code-acp
"""

import argparse
import asyncio
import logging
import os
import sys

from .server import run_proxy_server


def setup_logging(log_level: str) -> None:
    """Set up logging based on log level."""
    level_map = {
        "none": logging.CRITICAL + 1,
        "error": logging.ERROR,
        "warning": logging.WARNING,
        "info": logging.INFO,
        "debug": logging.DEBUG,
        "all": logging.DEBUG,
    }
    level = level_map.get(log_level.lower(), logging.INFO)

    # Log to stderr to avoid interfering with stdio communication
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="ACP Proxy - Bridge Copilot SDK to any ACP backend",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Connect to Gemini CLI
    copilot-acp-proxy --headless --stdio --backend gemini

    # Connect to claude-code-acp
    copilot-acp-proxy --headless --stdio --backend claude-code-acp

    # Connect to Copilot CLI (for testing)
    copilot-acp-proxy --headless --stdio --backend copilot

Environment Variables:
    ACP_PROXY_BACKEND       Default backend (default: gemini)
    ACP_PROXY_LOG_LEVEL     Log level (default: warning)
""",
    )

    # Copilot SDK compatibility flags (mostly ignored but accepted)
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run in headless mode (accepted for compatibility)",
    )
    parser.add_argument(
        "--server",
        action="store_true",
        help="Run as server (accepted for compatibility)",
    )
    parser.add_argument(
        "--stdio",
        action="store_true",
        help="Use stdio for communication (default)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=0,
        help="TCP port for server mode (not yet supported)",
    )
    parser.add_argument(
        "--log-level",
        default=os.environ.get("ACP_PROXY_LOG_LEVEL", "warning"),
        choices=["none", "error", "warning", "info", "debug", "all"],
        help="Log level",
    )
    parser.add_argument(
        "--auth-token-env",
        default="",
        help="Environment variable for auth token (ignored)",
    )
    parser.add_argument(
        "--no-auto-login",
        action="store_true",
        help="Disable auto login (ignored)",
    )

    # Proxy-specific flags
    parser.add_argument(
        "--backend",
        default=os.environ.get("ACP_PROXY_BACKEND", "gemini"),
        help="Backend ACP server to connect to (gemini, claude-code-acp, copilot)",
    )
    parser.add_argument(
        "--backend-args",
        nargs="*",
        default=[],
        help="Additional arguments for the backend CLI",
    )
    parser.add_argument(
        "--cwd",
        default=os.getcwd(),
        help="Working directory",
    )

    args = parser.parse_args()

    # Set up logging
    setup_logging(args.log_level)

    logger = logging.getLogger(__name__)
    logger.info(f"Starting ACP Proxy (backend: {args.backend})")

    # Check for TCP mode (not yet supported)
    if args.port > 0:
        logger.error("TCP mode (--port) is not yet supported")
        sys.exit(1)

    # Run the proxy server
    try:
        asyncio.run(
            run_proxy_server(
                backend=args.backend,
                backend_args=args.backend_args,
                cwd=args.cwd,
            )
        )
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
