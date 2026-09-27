"""
Priority-based resource allocation.
Score = Severity(0.4) + Population(0.3) + Accessibility(0.2) + Vulnerability(0.1)
"""

from __future__ import annotations

import os
import sys
from typing import Any

if os.path.dirname(os.path.abspath(__file__)) not in sys.path:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from district_info import available_resources, district_data
except ImportError:
    from scripts.district_info import available_resources, district_data

SEVERITY_MAP = {0: 0, 1: 4, 2: 7, 3: 10, 4: 10}
ACCESSIBILITY_MAP = {"High": 3, "Medium": 6, "Low": 10}


def calculate_priority_score(district_name: str, risk_level: int, risk_probability: float) -> float:
    if district_name not in district_data:
        print(f"⚠️ Warning: {district_name} not found in database")
        return 0.0

    info = district_data[district_name]
    severity_score = SEVERITY_MAP.get(int(risk_level), 0) * float(risk_probability)
    max_population = 1529958
    population_score = (info["population"] / max_population) * 10
    accessibility_score = ACCESSIBILITY_MAP.get(info["road_connectivity"], 5)
    vulnerability_score = min(len(info.get("vulnerable_areas", [])) * 3, 10)
    priority_score = (
        severity_score * 0.4
        + population_score * 0.3
        + accessibility_score * 0.2
        + vulnerability_score * 0.1
    )
    return round(priority_score, 2)


def allocate_resources(affected_districts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    priorities: list[dict[str, Any]] = []
    for district in affected_districts:
        district_name = district["district"]
        if district_name not in district_data:
            continue
        score = calculate_priority_score(
            district_name,
            district["risk_level"],
            district["risk_probability"],
        )
        priorities.append(
            {
                "district": district_name,
                "risk_level": district["risk_level"],
                "priority_score": score,
                "population": district_data[district_name]["population"],
                "accessibility": district_data[district_name]["road_connectivity"],
                "vulnerable_areas": district_data[district_name]["vulnerable_areas"],
                "hospitals": district_data[district_name]["hospitals"],
            }
        )

    priorities = sorted(priorities, key=lambda item: item["priority_score"], reverse=True)
    allocation_plan: list[dict[str, Any]] = []
    available_teams = available_resources["rescue_teams"].copy()
    remaining_supplies = available_resources["relief_supplies"].copy()

    for district in priorities:
        if district["risk_level"] == 0:
            continue
        if district["risk_level"] >= 3:
            teams_needed, supplies_factor = 3, 3
        elif district["risk_level"] == 2:
            teams_needed, supplies_factor = 2, 2
        else:
            teams_needed, supplies_factor = 1, 1

        pop_thousands = district["population"] / 1000
        supplies_needed = {
            "food_packets": int(pop_thousands * 2 * supplies_factor),
            "water_kits": int(pop_thousands * 3 * supplies_factor),
            "blankets": int(pop_thousands * 1 * supplies_factor),
            "medical_kits": int(district["hospitals"] * 10 * supplies_factor),
            "tents": int(pop_thousands * 0.5 * supplies_factor),
        }

        allocated_teams = []
        for _ in range(min(teams_needed, len(available_teams))):
            allocated_teams.append(available_teams.pop(0))

        supply_status = {}
        for item, needed in supplies_needed.items():
            available = remaining_supplies.get(item, 0)
            allocated = min(needed, available)
            remaining_supplies[item] = available - allocated
            supply_status[item] = {
                "needed": needed,
                "allocated": allocated,
                "shortage": max(0, needed - allocated),
            }

        allocation_plan.append(
            {
                "district": district["district"],
                "priority_score": district["priority_score"],
                "risk_level": district["risk_level"],
                "allocated_teams": allocated_teams,
                "supply_allocation": supply_status,
                "vulnerable_areas": district["vulnerable_areas"],
            }
        )
    return allocation_plan


if __name__ == "__main__":
    print("\n🚨 TESTING RESOURCE ALLOCATION SYSTEM\n")
    test_scenario = [
        {"district": "Jammu", "risk_level": 2, "risk_probability": 0.75},
        {"district": "Srinagar", "risk_level": 3, "risk_probability": 0.90},
        {"district": "Kupwara", "risk_level": 2, "risk_probability": 0.65},
    ]
    plan = allocate_resources(test_scenario)
    print("📊 RESOURCE ALLOCATION PLAN\n")
    for i, allocation in enumerate(plan, 1):
        print(f"{i}. {allocation['district']} (Priority: {allocation['priority_score']})")
        print(f"   Risk Level: {allocation['risk_level']}")
        print(f"   Teams: {len(allocation['allocated_teams'])}")
    print("✅ Test complete!")
