"""Verify Chapter 5 latency targets: prediction < 0.3s, allocation < 1.0s."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("WEATHER_PROVIDER", "dummy")

from agents.resource_agent import ResourceAgent  # noqa: E402
from scripts.settings import ALLOCATION_SLA_SECONDS, PREDICTION_SLA_SECONDS  # noqa: E402


def main() -> None:
    agent = ResourceAgent()
    response = agent.run_allocation(use_live=True)
    if response.get("type") == "error":
        raise SystemExit(response.get("response_text"))
    metrics = response.get("metrics") or {}
    pred = float(metrics["prediction_seconds"])
    alloc = float(metrics["allocation_seconds"])
    print(f"prediction_seconds={pred:.4f} (SLA {PREDICTION_SLA_SECONDS})")
    print(f"allocation_seconds={alloc:.4f} (SLA {ALLOCATION_SLA_SECONDS})")
    if pred >= PREDICTION_SLA_SECONDS or alloc >= ALLOCATION_SLA_SECONDS:
        raise SystemExit("Latency SLA missed.")
    print("SLA OK")


if __name__ == "__main__":
    main()
