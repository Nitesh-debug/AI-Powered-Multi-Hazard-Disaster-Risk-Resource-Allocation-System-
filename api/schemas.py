from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PredictionRequest(BaseModel):
    mode: Literal["historical_replay", "live", "simulated_demo"] = "historical_replay"


class AllocationRequest(BaseModel):
    run_id: str = Field(min_length=1)
