"""
ACP Proxy - Bridge Copilot SDK to any ACP-compatible CLI.

This module provides a proxy server that allows Copilot SDK to connect
to any ACP-compatible backend (Gemini CLI, claude-code-acp, etc.).

Architecture:
    Copilot SDK → ACP Proxy → Backend CLI (gemini/claude-code-acp)
"""

from .server import AcpProxyServer
from .session_manager import ProxySessionManager

__all__ = ["AcpProxyServer", "ProxySessionManager"]
