from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from api.config import PROJECT_ROOT

SCENARIO_PATH = PROJECT_ROOT / "data/development/phase9_simulated_scenario_v1.json"
SIMULATION_VERSION = "phase9_simulation_v1"
SIMULATION_STATUS = "SIMULATION_ONLY_NOT_FOR_DISPATCH"


def load_scenario(path: Path = SCENARIO_PATH) -> dict[str, Any]:
    scenario = json.loads(path.read_text(encoding="utf-8"))
    if (
        scenario.get("artifact_type") != "simulated_resource_planning_scenario"
        or scenario.get("simulation_version") != SIMULATION_VERSION
        or scenario.get("data_scope") != "SIMULATED_DEVELOPMENT_ONLY"
        or scenario.get("operational_status") != SIMULATION_STATUS
    ):
        raise RuntimeError("Simulated planning scenario failed scope/version validation")
    districts = set(scenario.get("district_order", []))
    resources = scenario.get("resources", [])
    exposure = scenario.get("exposure", [])
    travel = scenario.get("travel_time_matrix", [])
    if len(districts) != 20 or {item.get("district") for item in exposure} != districts:
        raise RuntimeError("Simulated scenario must cover the 20 model districts in its exposure table")
    if len(travel) != len(districts) ** 2 or len({item.get("resource_id") for item in resources}) != len(resources):
        raise RuntimeError("Simulated scenario has incomplete travel coverage or duplicate resource IDs")
    if any(item.get("simulation_version") != SIMULATION_VERSION or item.get("data_scope") != "SIMULATED_DEVELOPMENT_ONLY" for item in resources + exposure):
        raise RuntimeError("Simulated scenario contains a record without explicit simulation metadata")
    if any(item.get("simulation_version") != SIMULATION_VERSION for item in travel):
        raise RuntimeError("Travel-time records are missing simulation metadata")
    if any(item.get("available_capacity", -1) < 0 or item.get("total_capacity", -1) < item.get("available_capacity", 0) for item in resources):
        raise RuntimeError("Simulated resource capacity is invalid")
    return scenario


def resources_for_district(scenario: dict[str, Any], district: str | None = None) -> list[dict[str, Any]]:
    records = scenario["resources"]
    if district is not None:
        records = [item for item in records if item["district"] == district]
    return records


def exposure_for_district(scenario: dict[str, Any], district: str | None = None) -> list[dict[str, Any]]:
    records = scenario["exposure"]
    if district is not None:
        records = [item for item in records if item["district"] == district]
    return records
