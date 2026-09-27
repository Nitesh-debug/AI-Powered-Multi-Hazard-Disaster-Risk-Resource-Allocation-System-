from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.build_phase9_simulated_scenario import (  # noqa: E402
    SCENARIO,
    SIMULATION_VERSION,
    WEATHER_FIXTURE,
    WEATHER_SCOPE,
    make_scenario,
    make_weather_fixture,
)


def main() -> None:
    replay_path = ROOT / "data/development/replay_features/phase8_historical_replay_2025-10-31.json"
    replay = json.loads(replay_path.read_text(encoding="utf-8"))
    scenario = json.loads(SCENARIO.read_text(encoding="utf-8"))
    fixture = json.loads(WEATHER_FIXTURE.read_text(encoding="utf-8"))
    assert scenario == make_scenario(replay), "scenario is not reproducible from its deterministic builder"
    assert fixture == make_weather_fixture(replay), "weather fixture is not reproducible from its deterministic builder"
    districts = set(replay["districts"])
    assert len(districts) == 20
    assert scenario["data_scope"] == "SIMULATED_DEVELOPMENT_ONLY"
    assert scenario["simulation_version"] == SIMULATION_VERSION
    assert len(scenario["resources"]) == 140
    assert len({item["resource_id"] for item in scenario["resources"]}) == 140
    assert {item["resource_type"] for item in scenario["resources"]} == {
        "response_team", "ambulance", "medical_kits", "water_food_supplies", "shelter", "hospital", "resource_depot",
    }
    assert len(scenario["exposure"]) == 20
    assert {item["district"] for item in scenario["exposure"]} == districts
    assert len(scenario["travel_time_matrix"]) == 400
    assert len({(item["from_district"], item["to_district"]) for item in scenario["travel_time_matrix"]}) == 400
    for record in scenario["resources"] + scenario["exposure"]:
        assert record["data_scope"] == "SIMULATED_DEVELOPMENT_ONLY"
        assert record["simulation_version"] == SIMULATION_VERSION
    for record in scenario["resources"]:
        assert 0 <= record["available_capacity"] <= record["total_capacity"]
    assert fixture["weather_scope"] == WEATHER_SCOPE
    assert fixture["fixture_version"] == "phase9_demo_weather_v1"
    assert set(fixture["districts"]) == districts
    for record in fixture["districts"].values():
        assert len(record["features"]) == 68
        assert all(math.isfinite(float(value)) for value in record["features"].values())
    assert "not observed weather" in fixture["generation_note"]
    print("Phase 9 artifact validation passed: 140 resources, 20 exposure rows, 400 travel pairs, 20 x 68 labelled demo-weather fixture.")


if __name__ == "__main__":
    main()
