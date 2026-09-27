from __future__ import annotations

from collections import defaultdict
from typing import Any

MAX_SIMULATED_TRAVEL_MINUTES = 240.0
PRIORITY_FORMULA = (
    "priority = 30*risk + 25*simulated_exposure + 20*simulated_vulnerability "
    "+ 15*development_severity + 10*signal_urgency; each component is normalized to 0-1, "
    "then the sum is capped at 100. Risk scores are raw uncalibrated synthetic-model scores."
)
SIMULATION_DISCLAIMER = "SIMULATION_ONLY_NOT_FOR_DISPATCH; not for public warning, real stock decisions, or emergency operations."

HAZARD_RESOURCE_NEEDS = {
    "flood": {"response_team": 1, "ambulance": 1, "medical_kits": 8, "water_food_supplies": 15, "shelter": 25, "hospital": 5, "resource_depot": 1},
    "heavy_rain": {"response_team": 1, "ambulance": 1, "medical_kits": 6, "water_food_supplies": 12, "shelter": 20, "hospital": 5, "resource_depot": 1},
    "landslide": {"response_team": 1, "ambulance": 1, "medical_kits": 8, "water_food_supplies": 8, "shelter": 20, "hospital": 5, "resource_depot": 1},
    "heatwave": {"ambulance": 1, "medical_kits": 10, "water_food_supplies": 20, "hospital": 8, "resource_depot": 1},
    "coldwave": {"ambulance": 1, "medical_kits": 8, "water_food_supplies": 15, "shelter": 30, "hospital": 5, "resource_depot": 1},
    "windstorm": {"response_team": 1, "ambulance": 1, "medical_kits": 8, "water_food_supplies": 8, "shelter": 20, "hospital": 5, "resource_depot": 1},
}


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def calculate_priority(raw_risk: float, exposure: float, vulnerability: float, active_signal_count: int) -> dict[str, float]:
    risk = clamp01(raw_risk)
    exposure_component = clamp01(exposure)
    vulnerability_component = clamp01(vulnerability)
    severity = 1.0 if risk >= 0.75 else 0.75 if risk >= 0.50 else 0.50 if risk >= 0.25 else 0.25
    urgency = min(max(active_signal_count, 0), 3) / 3.0
    components = {
        "risk_component": round(30.0 * risk, 2),
        "exposure_component": round(25.0 * exposure_component, 2),
        "vulnerability_component": round(20.0 * vulnerability_component, 2),
        "severity_component": round(15.0 * severity, 2),
        "urgency_component": round(10.0 * urgency, 2),
    }
    components["priority_score"] = round(min(100.0, sum(components.values())), 2)
    return components


def _legacy_assignment(assignments: list[dict[str, Any]]) -> dict[str, int]:
    legacy = {"response_team_slots": 0, "medical_kit_slots": 0, "water_crate_slots": 0}
    aliases = {"response_team": "response_team_slots", "medical_kits": "medical_kit_slots", "water_food_supplies": "water_crate_slots"}
    for assignment in assignments:
        target = aliases.get(assignment["resource_type"])
        if target:
            legacy[target] += int(assignment["allocated_capacity"])
    return legacy


def build_response_plan(run: dict[str, Any], scenario: dict[str, Any]) -> dict[str, Any]:
    exposures = {record["district"]: record for record in scenario["exposure"]}
    travel = {(record["from_district"], record["to_district"]): record["travel_time_minutes"] for record in scenario["travel_time_matrix"]}
    remaining = {record["resource_id"]: int(record["available_capacity"]) for record in scenario["resources"]}
    used_resource_ids: set[str] = set()
    resources_by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for resource in scenario["resources"]:
        resources_by_type[resource["resource_type"]].append(resource)

    district_plans = []
    for district_result in run.get("district_results", []):
        if district_result.get("status") != "complete":
            continue
        district = district_result["district"]
        exposure = exposures[district]
        hazards = district_result.get("hazards", [])
        active = [item for item in hazards if item.get("above_validation_threshold")]
        raw_risk = max((float(item["raw_model_score"]) for item in hazards), default=0.0)
        components = calculate_priority(
            raw_risk,
            exposure["simulated_exposure_index"],
            exposure["simulated_vulnerability_index"],
            len(active),
        )
        district_plans.append({
            "district": district,
            "result": district_result,
            "exposure": exposure,
            "active_hazards": active,
            "raw_risk": raw_risk,
            "priority_components": components,
        })
    district_plans.sort(key=lambda item: (-item["priority_components"]["priority_score"], item["district"]))

    recommendations = []
    for plan in district_plans:
        district = plan["district"]
        active_hazards = plan["active_hazards"]
        active_names = [item["hazard"] for item in active_hazards]
        needs: dict[str, int] = defaultdict(int)
        for hazard in active_names:
            for resource_type, quantity in HAZARD_RESOURCE_NEEDS.get(hazard, {}).items():
                needs[resource_type] = max(needs[resource_type], quantity)

        assignments = []
        unmet = []
        for resource_type in sorted(needs):
            candidates = []
            for resource in resources_by_type[resource_type]:
                minutes = float(travel[(resource["district"], district)])
                if (
                    remaining[resource["resource_id"]] > 0
                    and resource["resource_id"] not in used_resource_ids
                    and any(hazard in resource["suitable_hazards"] for hazard in active_names)
                    and minutes <= MAX_SIMULATED_TRAVEL_MINUTES
                ):
                    candidates.append((minutes, resource["resource_id"], resource))
            candidates.sort(key=lambda item: (item[0], item[1]))
            if not candidates:
                unmet.append({
                    "resource_type": resource_type,
                    "requested_capacity": needs[resource_type],
                    "reason": f"No available compatible simulated resource is within {MAX_SIMULATED_TRAVEL_MINUTES:.0f} simulated travel minutes.",
                })
                continue
            minutes, _, resource = candidates[0]
            allocated = min(needs[resource_type], remaining[resource["resource_id"]])
            remaining[resource["resource_id"]] -= allocated
            used_resource_ids.add(resource["resource_id"])
            assignments.append({
                "resource_id": resource["resource_id"],
                "resource_type": resource_type,
                "resource_district": resource["district"],
                "allocated_capacity": allocated,
                "capacity_unit": resource["capacity_unit"],
                "estimated_travel_time_minutes": minutes,
                "travel_time_scope": "SIMULATED_ESTIMATE_NOT_ROUTED",
                "compatible_hazards": [hazard for hazard in active_names if hazard in resource["suitable_hazards"]],
                "status": "SIMULATED_RECOMMENDATION_NOT_DISPATCH",
                "simulation_version": scenario["simulation_version"],
            })
            if allocated < needs[resource_type]:
                unmet.append({
                    "resource_type": resource_type,
                    "requested_capacity": needs[resource_type] - allocated,
                    "reason": "Available simulated capacity was below the requested scenario quantity.",
                })

        exposure_index = float(plan["exposure"]["simulated_exposure_index"])
        vulnerability_index = float(plan["exposure"]["simulated_vulnerability_index"])
        hazard_phrase = ", ".join(active_names) if active_names else "no threshold-exceeding development signal"
        reason = (
            f"{hazard_phrase}; raw synthetic score {plan['raw_risk']:.4f}; simulated exposure {exposure_index:.2f}; "
            f"simulated vulnerability {vulnerability_index:.2f}. Recommended quantities are limited by this scenario's "
            "synthetic availability, compatibility, capacity, and travel-time estimate."
        )
        if not active_names:
            reason = "No hazard exceeded its validation-selected synthetic development threshold; no resources are recommended."
        recommendations.append({
            "district": district,
            "hazards": active_names,
            "risk_score": plan["raw_risk"],
            "risk_score_semantics": "maximum raw uncalibrated synthetic-model score; not a probability",
            "priority_score": plan["priority_components"]["priority_score"],
            "simulation_priority": plan["priority_components"]["priority_score"],
            "raw_model_score": plan["raw_risk"],
            "development_signals": active_names,
            "priority_components": plan["priority_components"],
            "simulated_population": plan["exposure"]["simulated_population"],
            "simulated_exposure_index": exposure_index,
            "simulated_vulnerability_index": vulnerability_index,
            "resource_assignments": assignments,
            "unmet_needs": unmet,
            "simulated_assignment": _legacy_assignment(assignments),
            "estimated_travel_time_minutes": min((item["estimated_travel_time_minutes"] for item in assignments), default=None),
            "allocation_reason": reason,
            "data_scope": "SIMULATED_DEVELOPMENT_ONLY",
            "simulation_version": scenario["simulation_version"],
        })

    initial_by_type: dict[str, int] = defaultdict(int)
    remaining_by_type: dict[str, int] = defaultdict(int)
    for resource in scenario["resources"]:
        resource_type = resource["resource_type"]
        initial_by_type[resource_type] += int(resource["available_capacity"])
        remaining_by_type[resource_type] += remaining[resource["resource_id"]]
    inventory_items = {
        "response_team_slots": initial_by_type["response_team"],
        "ambulance_slots": initial_by_type["ambulance"],
        "medical_kit_slots": initial_by_type["medical_kits"],
        "water_crate_slots": initial_by_type["water_food_supplies"],
        "shelter_person_capacity": initial_by_type["shelter"],
        "hospital_bed_slots": initial_by_type["hospital"],
        "resource_depot_slots": initial_by_type["resource_depot"],
    }
    inventory_remaining = {
        "response_team_slots": remaining_by_type["response_team"],
        "ambulance_slots": remaining_by_type["ambulance"],
        "medical_kit_slots": remaining_by_type["medical_kits"],
        "water_crate_slots": remaining_by_type["water_food_supplies"],
        "shelter_person_capacity": remaining_by_type["shelter"],
        "hospital_bed_slots": remaining_by_type["hospital"],
        "resource_depot_slots": remaining_by_type["resource_depot"],
    }
    return {
        "prediction_run_id": run.get("id"),
        "model_version": run.get("model_version"),
        "weather_data_timestamp": run.get("data_freshness"),
        "simulation_version": scenario["simulation_version"],
        "operational_status": SIMULATION_DISCLAIMER,
        "priority_formula": PRIORITY_FORMULA,
        "max_simulated_travel_minutes": MAX_SIMULATED_TRAVEL_MINUTES,
        "recommendations": recommendations,
        "allocations": [item for item in recommendations if item["resource_assignments"]],
        "inventory": {
            "scope": "SIMULATED_DEVELOPMENT_ONLY",
            "source": "versioned deterministic scenario artifact; not official or live inventory",
            "items": inventory_items,
            "remaining": inventory_remaining,
        },
        "input_availability": {
            "exposure": "simulated development data",
            "vulnerability": "simulated development data",
            "resource_suitability": "simulated hazard compatibility table",
            "resource_availability": "simulated development data",
            "travel_time": "simulated estimate; not road-routed",
            "capacity": "simulated development data",
            "authoritative_operational_inputs": "unavailable",
        },
        "allocation_reason": "Deterministic priority ordering followed by nearest compatible available resources within the simulated travel-time limit; each resource ID is assigned at most once.",
        "status": "SIMULATION_ONLY_NOT_FOR_DISPATCH",
    }
