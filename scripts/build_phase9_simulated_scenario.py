from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPLAY = ROOT / "data/development/replay_features/phase8_historical_replay_2025-10-31.json"
SCENARIO = ROOT / "data/development/phase9_simulated_scenario_v1.json"
WEATHER_FIXTURE = ROOT / "data/development/phase9_simulated_weather_fixture_v1.json"
SIMULATION_VERSION = "phase9_simulation_v1"
WEATHER_FIXTURE_VERSION = "phase9_demo_weather_v1"
WEATHER_SCOPE = "SIMULATED_DEMO_WEATHER"
RESOURCE_HAZARDS = {
    "response_team": ["flood", "heavy_rain", "landslide", "windstorm"],
    "ambulance": ["flood", "heavy_rain", "landslide", "heatwave", "coldwave", "windstorm"],
    "medical_kits": ["flood", "heavy_rain", "landslide", "heatwave", "coldwave", "windstorm"],
    "water_food_supplies": ["flood", "heavy_rain", "landslide", "heatwave", "coldwave", "windstorm"],
    "shelter": ["flood", "heavy_rain", "landslide", "coldwave", "windstorm"],
    "hospital": ["flood", "heavy_rain", "landslide", "heatwave", "coldwave", "windstorm"],
    "resource_depot": ["flood", "heavy_rain", "landslide", "heatwave", "coldwave", "windstorm"],
}


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def road_minutes(origin: dict[str, Any], destination: dict[str, Any], origin_index: int, destination_index: int) -> float:
    lat1, lon1 = math.radians(origin["latitude"]), math.radians(origin["longitude"])
    lat2, lon2 = math.radians(destination["latitude"]), math.radians(destination["longitude"])
    delta_lat, delta_lon = lat2 - lat1, lon2 - lon1
    haversine = 2 * 6371 * math.asin(math.sqrt(
        math.sin(delta_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    ))
    if origin_index == destination_index:
        return 8.0
    road_distance_estimate = haversine * 1.45
    simulated_delay = 8 + ((origin_index * 7 + destination_index * 11) % 23)
    return round(road_distance_estimate / 38 * 60 + simulated_delay, 1)


def make_resource(resource_type: str, district: str, index: int, latitude: float, longitude: float) -> dict[str, Any]:
    definitions = {
        "response_team": (1, 0 if index % 7 == 6 else 1, "team_slot"),
        "ambulance": (1, 0 if index % 9 == 8 else 1, "vehicle_slot"),
        "medical_kits": (80, 18 + (index * 13) % 53, "kit"),
        "water_food_supplies": (240, 55 + (index * 29) % 161, "supply_pack"),
        "shelter": (420, 90 + (index * 47) % 301, "person_capacity"),
        "hospital": (110, 12 + (index * 17) % 83, "bed_slot"),
        "resource_depot": (1, 1, "depot_slot"),
    }
    total, available, unit = definitions[resource_type]
    return {
        "resource_id": f"SIM-P9-{resource_type}-{slug(district)}",
        "resource_type": resource_type,
        "district": district,
        "latitude": latitude,
        "longitude": longitude,
        "coordinate_semantics": "weather reference point used as an illustrative simulated node; not a verified facility location",
        "available_capacity": available,
        "total_capacity": total,
        "capacity_unit": unit,
        "status": "unavailable" if available == 0 else ("limited" if available < total * 0.35 else "available"),
        "suitable_hazards": RESOURCE_HAZARDS[resource_type],
        "data_scope": "SIMULATED_DEVELOPMENT_ONLY",
        "simulation_version": SIMULATION_VERSION,
    }


def make_scenario(replay: dict[str, Any]) -> dict[str, Any]:
    districts = replay["districts"]
    names = list(districts)
    resources = [
        make_resource(resource_type, district, index, float(districts[district]["latitude"]), float(districts[district]["longitude"]))
        for index, district in enumerate(names)
        for resource_type in RESOURCE_HAZARDS
    ]
    exposure = []
    for index, district in enumerate(names):
        population = 42000 + (index * 18731) % 310000
        exposure_index = round(0.18 + ((index * 37) % 71) / 100, 3)
        vulnerability_index = round(0.22 + ((index * 29 + 13) % 67) / 100, 3)
        exposure.append({
            "district": district,
            "simulated_population": population,
            "simulated_exposure_index": exposure_index,
            "simulated_vulnerability_index": vulnerability_index,
            "data_scope": "SIMULATED_DEVELOPMENT_ONLY",
            "simulation_version": SIMULATION_VERSION,
        })
    travel = []
    for origin_index, origin_name in enumerate(names):
        for destination_index, destination_name in enumerate(names):
            origin = districts[origin_name]
            destination = districts[destination_name]
            travel.append({
                "from_district": origin_name,
                "to_district": destination_name,
                "travel_time_minutes": road_minutes(origin, destination, origin_index, destination_index),
                "route_status": "SIMULATED_ESTIMATE_NOT_ROUTED",
                "simulation_version": SIMULATION_VERSION,
            })
    return {
        "artifact_type": "simulated_resource_planning_scenario",
        "simulation_version": SIMULATION_VERSION,
        "data_scope": "SIMULATED_DEVELOPMENT_ONLY",
        "operational_status": "SIMULATION_ONLY_NOT_FOR_DISPATCH",
        "district_order": names,
        "limitations": [
            "Every population, exposure, vulnerability, facility, stock and capacity value is deterministic demonstration data, not an official statistic or inventory.",
            "Coordinates are weather lookup reference points, not verified facility locations, district centroids or boundaries.",
            "Travel times are synthetic estimates from straight-line distance and fixed assumptions; no road graph or live routing service is used.",
        ],
        "resources": resources,
        "exposure": exposure,
        "travel_time_matrix": travel,
    }


def make_weather_fixture(replay: dict[str, Any]) -> dict[str, Any]:
    rows = {}
    for index, (district, record) in enumerate(replay["districts"].items()):
        offset = ((index % 5) - 2) * 1.6
        rain_scale = 0.55 + (index % 6) * 0.18
        wind_scale = 0.78 + (index % 4) * 0.13
        features = {}
        for name, raw_value in record["features"].items():
            value = float(raw_value)
            if "temperature" in name:
                value += offset
            elif any(token in name for token in ("precipitation", "rain", "snowfall", "snow_depth")):
                value *= rain_scale
            elif "wind_speed" in name or "wind_gust" in name:
                value *= wind_scale
            elif "humidity" in name:
                value = min(100.0, max(0.0, value + ((index % 3) - 1) * 4.0))
            features[name] = round(value, 6)
        rows[district] = {
            "latitude": float(record["latitude"]),
            "longitude": float(record["longitude"]),
            "features": features,
        }
    return {
        "artifact_type": "synthetic_demo_weather_fixture",
        "weather_scope": WEATHER_SCOPE,
        "fixture_version": WEATHER_FIXTURE_VERSION,
        "feature_reference_date": replay["feature_reference_date"],
        "target_date": replay["target_date"],
        "feature_schema_version": "phase5_68_shifted_weather_v1",
        "generation_note": "Deterministic perturbations of an existing replay feature snapshot for offline UI/API demonstration; not observed weather and not for scientific evaluation.",
        "districts": rows,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build explicitly simulated Phase 9 demo scenario artifacts.")
    parser.add_argument("--check", action="store_true", help="Validate existing outputs without rewriting them.")
    args = parser.parse_args()
    replay = json.loads(REPLAY.read_text(encoding="utf-8"))
    expected = {
        SCENARIO: make_scenario(replay),
        WEATHER_FIXTURE: make_weather_fixture(replay),
    }
    if args.check:
        for path, payload in expected.items():
            if not path.exists() or json.loads(path.read_text(encoding="utf-8")) != payload:
                raise SystemExit(f"Generated artifact differs or is missing: {path.relative_to(ROOT)}")
    else:
        for path, payload in expected.items():
            write_json(path, payload)
            print(f"Wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
