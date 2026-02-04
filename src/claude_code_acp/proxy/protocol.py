"""
Copilot SDK Protocol definitions.

This module defines the JSON-RPC methods and data structures
expected by the Copilot SDK.
"""

from dataclasses import dataclass, field
from typing import Any, Literal
from enum import Enum


# ============================================================================
# Request/Response Types
# ============================================================================

@dataclass
class PingRequest:
    message: str = ""


@dataclass
class PingResponse:
    message: str
    timestamp: int  # Unix timestamp in ms
    protocolVersion: int = 1


@dataclass
class StatusResponse:
    version: str
    protocolVersion: int = 1


@dataclass
class AuthStatusResponse:
    isAuthenticated: bool
    authType: str  # "user" | "env" | "gh-cli" | "hmac" | "api-key" | "token"
    host: str = ""
    login: str = ""
    statusMessage: str = ""


@dataclass
class ModelInfo:
    id: str
    name: str
    capabilities: dict = field(default_factory=dict)
    policy: dict = field(default_factory=dict)
    billing: dict = field(default_factory=dict)


@dataclass
class ModelsListResponse:
    models: list[ModelInfo] = field(default_factory=list)


# ============================================================================
# Session Types
# ============================================================================

@dataclass
class SessionCreateParams:
    model: str | None = None
    sessionId: str | None = None
    reasoningEffort: str | None = None
    tools: list[dict] | None = None
    systemMessage: dict | None = None
    availableTools: list[str] | None = None
    excludedTools: list[str] | None = None
    provider: dict | None = None  # BYOK
    requestPermission: bool = False
    requestUserInput: bool = False
    hooks: bool = False
    workingDirectory: str | None = None
    streaming: bool = False
    mcpServers: dict | None = None
    customAgents: list[dict] | None = None
    configDir: str | None = None
    skillDirectories: list[str] | None = None
    disabledSkills: list[str] | None = None
    infiniteSessions: dict | None = None


@dataclass
class SessionCreateResponse:
    sessionId: str
    workspacePath: str | None = None


@dataclass
class SessionSendParams:
    sessionId: str
    prompt: str
    attachments: list[dict] | None = None
    mode: str = "enqueue"  # "enqueue" | "immediate"


@dataclass
class SessionSendResponse:
    messageId: str


@dataclass
class SessionDestroyParams:
    sessionId: str


@dataclass
class SessionListResponse:
    sessions: list[dict] = field(default_factory=list)


@dataclass
class SessionMessagesResponse:
    events: list[dict] = field(default_factory=list)


# ============================================================================
# Event Types (CLI → SDK Notifications)
# ============================================================================

class SessionEventType(str, Enum):
    # Session lifecycle
    SESSION_START = "session.start"
    SESSION_RESUME = "session.resume"
    SESSION_ERROR = "session.error"
    SESSION_IDLE = "session.idle"
    SESSION_INFO = "session.info"
    SESSION_SHUTDOWN = "session.shutdown"

    # User message
    USER_MESSAGE = "user.message"

    # Assistant events
    ASSISTANT_TURN_START = "assistant.turn_start"
    ASSISTANT_INTENT = "assistant.intent"
    ASSISTANT_REASONING = "assistant.reasoning"
    ASSISTANT_REASONING_DELTA = "assistant.reasoning_delta"
    ASSISTANT_MESSAGE = "assistant.message"
    ASSISTANT_MESSAGE_DELTA = "assistant.message_delta"
    ASSISTANT_TURN_END = "assistant.turn_end"
    ASSISTANT_USAGE = "assistant.usage"

    # Tool events
    TOOL_EXECUTION_START = "tool.execution_start"
    TOOL_EXECUTION_PROGRESS = "tool.execution_progress"
    TOOL_EXECUTION_COMPLETE = "tool.execution_complete"

    # Abort
    ABORT = "abort"


@dataclass
class SessionEvent:
    type: str
    data: dict = field(default_factory=dict)


# ============================================================================
# Tool Call Types (CLI → SDK Requests)
# ============================================================================

@dataclass
class ToolCallRequest:
    sessionId: str
    toolCallId: str
    toolName: str
    arguments: dict = field(default_factory=dict)


@dataclass
class ToolCallResponse:
    result: dict  # {textResultForLlm, resultType, error?, toolTelemetry?}


# ============================================================================
# Permission Types
# ============================================================================

@dataclass
class PermissionRequest:
    sessionId: str
    permissionRequest: dict  # {kind, toolCallId?, ...}


@dataclass
class PermissionResponse:
    result: dict  # {kind: "approved" | "denied-*"}


# ============================================================================
# User Input Types
# ============================================================================

@dataclass
class UserInputRequest:
    sessionId: str
    question: str
    choices: list[str] | None = None
    allowFreeform: bool = True


@dataclass
class UserInputResponse:
    answer: str
    wasFreeform: bool = False


# ============================================================================
# Helper Functions
# ============================================================================

def create_session_event(event_type: SessionEventType | str, data: dict | None = None) -> dict:
    """Create a session event notification payload."""
    import uuid
    from datetime import datetime, timezone
    return {
        "id": str(uuid.uuid4()),  # SDK requires event ID
        "type": event_type.value if isinstance(event_type, SessionEventType) else event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),  # ISO 8601 timestamp
        "data": data or {}
    }


def create_assistant_message_event(content: str, message_id: str = "") -> dict:
    """Create an assistant message event."""
    return create_session_event(
        SessionEventType.ASSISTANT_MESSAGE,
        {
            "messageId": message_id,
            "content": content,
            "toolRequests": []
        }
    )


def create_assistant_message_delta_event(delta_content: str) -> dict:
    """Create an assistant message delta event for streaming."""
    return create_session_event(
        SessionEventType.ASSISTANT_MESSAGE_DELTA,
        {"deltaContent": delta_content}
    )


def create_tool_execution_start_event(
    tool_call_id: str,
    tool_name: str,
    arguments: dict | None = None
) -> dict:
    """Create a tool execution start event."""
    return create_session_event(
        SessionEventType.TOOL_EXECUTION_START,
        {
            "toolCallId": tool_call_id,
            "toolName": tool_name,
            "arguments": arguments or {}
        }
    )


def create_tool_execution_complete_event(
    tool_call_id: str,
    success: bool,
    result: Any = None
) -> dict:
    """Create a tool execution complete event."""
    return create_session_event(
        SessionEventType.TOOL_EXECUTION_COMPLETE,
        {
            "toolCallId": tool_call_id,
            "success": success,
            "result": result
        }
    )
