from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Agent(ABC):
    """Base class for the custom multi-agent (ADK-style) framework."""

    def __init__(self, name: str) -> None:
        self.name = name

    @abstractmethod
    def process_request(self, query: str) -> dict[str, Any]:
        """
        Process a user request and return a structured response.

        Response format:
        {
            "agent": str,
            "response_text": str,
            "data": Any,
            "type": str,
            "error": str | None,
            "metrics": dict[str, float] | None
        }
        """

    def _format_response(
        self,
        text: str,
        data: Any = None,
        resp_type: str = "text",
        error: str | None = None,
        metrics: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        return {
            "agent": self.name,
            "response_text": text,
            "data": data,
            "type": resp_type,
            "error": error,
            "metrics": metrics or {},
        }
