"""Master coordinator: NL intent parse -> sub-agent dispatch -> fallback."""

from __future__ import annotations

from typing import Any, Callable

from .analytics_agent import AnalyticsAgent
from .base_agent import Agent
from .notification_agent import NotificationAgent
from .resource_agent import ResourceAgent

# Keyword router (LangGraph/AutoGen upgrade path: replace _route() with an LLM
# classifier node, then keep the same dispatch map as graph edges.)
RESOURCE_INTENTS = (
    "allocate",
    "resource",
    "predict",
    "risk",
    "plan",
    "demo",
    "alert",
    "weather",
    "forecast",
)
ANALYTICS_INTENTS = (
    "map",
    "chart",
    "graph",
    "stat",
    "summary",
    "heatmap",
    "dashboard",
    "hospital",
    "direction",
    "show",
)


class MasterAgent(Agent):
    """Central router with last-intent state and error fallback."""

    def __init__(self) -> None:
        super().__init__("MasterAgent")
        self.resource_agent = ResourceAgent(self)
        self.analytics_agent = AnalyticsAgent()
        self.notification_agent = NotificationAgent()
        self.state: dict[str, Any] = {
            "last_intent": None,
            "last_agent": None,
            "last_error": None,
        }
        self._dispatch: dict[str, Callable[[str], dict[str, Any]]] = {
            "resource": self.resource_agent.process_request,
            "analytics": self.analytics_agent.process_request,
            "notify": self.notification_agent.process_request,
        }

    def _route(self, query: str) -> str:
        q = query.lower()
        if any(w in q for w in ("test sms", "test email", "test alert")):
            return "notify"
        analytics_keys = tuple(k for k in ANALYTICS_INTENTS if k != "show")
        if any(w in q for w in analytics_keys):
            return "analytics"
        if any(w in q for w in RESOURCE_INTENTS):
            return "resource"
        if "show" in q:
            return "analytics"
        return "unknown"

    def process_request(self, query: str) -> dict[str, Any]:
        intent = self._route(query)
        self.state["last_intent"] = intent

        if intent == "unknown":
            return self._format_response(
                "I am the Master Disaster Management Agent. I can help you with:\n"
                "1. **Resource Allocation**: 'Run resource allocation plan'\n"
                "2. **Analytics**: 'Show me the risk map' or 'Show summary stats'\n"
                "3. **Alerts**: 'Send test alert'"
            )

        try:
            response = self._dispatch[intent](query)
            self.state["last_agent"] = response.get("agent")
            self.state["last_error"] = response.get("error")
            if response.get("type") == "error":
                return self._fallback(query, response)
            return response
        except Exception as exc:
            self.state["last_error"] = str(exc)
            return self._fallback(query, self._format_response(str(exc), resp_type="error", error=str(exc)))

    def _fallback(self, query: str, failed: dict[str, Any]) -> dict[str, Any]:
        """If resource planning fails but prior results exist, serve analytics."""
        if self.state.get("last_intent") == "resource":
            analytics = self.analytics_agent.process_request("show summary stats")
            if analytics.get("type") != "error":
                analytics["response_text"] = (
                    f"Resource agent failed ({failed.get('response_text')}). "
                    f"Showing the latest stored analytics instead.\n\n{analytics['response_text']}"
                )
                return analytics
        return failed
