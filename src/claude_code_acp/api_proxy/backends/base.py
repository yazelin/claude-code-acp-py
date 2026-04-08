"""Backend abstraction for the api_proxy.

A backend is anything that takes a string prompt and returns a string
response. Tool calling is handled at the prompt_builder layer (via prompt
engineering), so backends only need to implement plain text → text.
"""

from __future__ import annotations

from typing import Protocol


class Backend(Protocol):
    """A pluggable text completion backend."""

    name: str

    async def query(self, prompt: str, *, model: str | None = None) -> str:
        """Send a prompt and return the model's text response.

        Args:
            prompt: The full flat prompt (already including system + tool
                protocol + history + the trailing "Assistant:").
            model: Optional model identifier. The backend may ignore this
                if it manages model selection elsewhere.

        Returns:
            The model's plain text response.
        """
        ...

    async def close(self) -> None:
        """Release any persistent resources held by the backend."""
        ...
