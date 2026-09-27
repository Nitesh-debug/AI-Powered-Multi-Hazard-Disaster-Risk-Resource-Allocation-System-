from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from api import main as api_main
from api.resource_planning import MAX_SIMULATED_TRAVEL_MINUTES, build_response_plan, calculate_priority
from api.resources import load_scenario
from api.store import DemoStore
from api.weather import replay_features


def tiny_scenario(*, travel_minutes: float = 45.0, compatible: bool = True, available: int = 30) -> dict:
    types = {
        "response_team": (1, "team_slot"),
        "ambulance": (1, "vehicle_slot"),
        "medical_kits": (available, "kit"),
        "water_food_supplies": (available, "supply_pack"),
        "shelter": (available, "person_capacity"),
        "hospital": (available, "bed_slot"),
        "resource_depot": (1, "depot_slot"),
    }
    resources = []
    for resource_type, (capacity, unit) in types.items():
        resources.append({
            "resource_id": f"SIM-{resource_type}",
            "resource_type": resource_type,
            "district": "Anantnag",
            "available_capacity": capacity,
            "total_capacity": capacity,
            "capacity_unit": unit,
            "suitable_hazards": ["flood"] if compatible else ["heatwave"],
        })
    return {
        "simulation_version": "phase9_simulation_test_v1",
        "resources": resources,
        "exposure": [
            {"district": "Anantnag", "simulated_population": 10000, "simulated_exposure_index": 0.8, "simulated_vulnerability_index": 0.7},
            {"district": "Bandipora", "simulated_population": 20000, "simulated_exposure_index": 0.8, "simulated_vulnerability_index": 0.7},
        ],
        "travel_time_matrix": [
            {"from_district": "Anantnag", "to_district": "Anantnag", "travel_time_minutes": 8},
            {"from_district": "Anantnag", "to_district": "Bandipora", "travel_time_minutes": travel_minutes},
        ],
    }


def tiny_run() -> dict:
    districts = []
    for district in ("Anantnag", "Bandipora"):
        districts.append({
            "district": district,
            "status": "complete",
            "hazards": [{"hazard": "flood", "raw_model_score": 0.8, "validation_threshold_score": 0.2, "above_validation_threshold": True}],
        })
    return {"id": "test-run", "model_version": "phase7f_v1", "data_freshness": {"status": "test"}, "district_results": districts}


class SimulatedResourceEngineTests(unittest.TestCase):
    def test_scenario_has_explicitly_simulated_records_and_full_matrix(self) -> None:
        scenario = load_scenario()
        self.assertEqual(scenario["simulation_version"], "phase9_simulation_v1")
        self.assertEqual(len(scenario["district_order"]), 20)
        self.assertEqual(len(scenario["exposure"]), 20)
        self.assertEqual(len(scenario["travel_time_matrix"]), 400)
        self.assertEqual(len(scenario["resources"]), 140)
        self.assertEqual({item["resource_type"] for item in scenario["resources"]}, {
            "response_team", "ambulance", "medical_kits", "water_food_supplies", "shelter", "hospital", "resource_depot",
        })
        for item in scenario["resources"] + scenario["exposure"]:
            self.assertEqual(item["data_scope"], "SIMULATED_DEVELOPMENT_ONLY")
            self.assertEqual(item["simulation_version"], "phase9_simulation_v1")

    def test_priority_components_are_bounded_and_explainable(self) -> None:
        score = calculate_priority(0.8, 0.6, 0.5, 2)
        self.assertEqual(score["risk_component"], 24.0)
        self.assertEqual(score["exposure_component"], 15.0)
        self.assertEqual(score["vulnerability_component"], 10.0)
        self.assertEqual(score["severity_component"], 15.0)
        self.assertAlmostEqual(score["urgency_component"], 6.67)
        self.assertLessEqual(score["priority_score"], 100)

    def test_no_resource_id_is_allocated_twice(self) -> None:
        plan = build_response_plan(tiny_run(), tiny_scenario())
        ids = [item["resource_id"] for row in plan["allocations"] for item in row["resource_assignments"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(plan["allocations"][0]["district"], "Anantnag")
        bandipora = next(item for item in plan["recommendations"] if item["district"] == "Bandipora")
        self.assertEqual(bandipora["resource_assignments"], [])
        self.assertTrue(bandipora["unmet_needs"])

    def test_suitability_capacity_and_travel_constraints(self) -> None:
        unsuitable = build_response_plan(tiny_run(), tiny_scenario(compatible=False))
        self.assertEqual(unsuitable["allocations"], [])
        too_far = build_response_plan(tiny_run(), tiny_scenario(travel_minutes=MAX_SIMULATED_TRAVEL_MINUTES + 1))
        bandipora = next(item for item in too_far["recommendations"] if item["district"] == "Bandipora")
        self.assertFalse(bandipora["resource_assignments"])
        low_stock = build_response_plan(tiny_run(), tiny_scenario(available=3))
        anantnag = next(item for item in low_stock["recommendations"] if item["district"] == "Anantnag")
        self.assertTrue(anantnag["unmet_needs"])


class Phase9SimulationApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.original_store = api_main.STORE
        api_main.STORE = DemoStore(Path(self.temp.name) / "phase9.sqlite3")
        self.client = TestClient(api_main.app)

    def tearDown(self) -> None:
        self.client.close()
        api_main.STORE = self.original_store
        self.temp.cleanup()

    def test_resources_exposure_and_demo_weather_api_contracts(self) -> None:
        resources = self.client.get("/api/resources")
        self.assertEqual(resources.status_code, 200)
        self.assertEqual(resources.json()["count"], 140)
        self.assertEqual(resources.json()["data_scope"], "SIMULATED_DEVELOPMENT_ONLY")
        exposure = self.client.get("/api/exposure?district=Srinagar")
        self.assertEqual(exposure.json()["count"], 1)
        self.assertEqual(exposure.json()["districts"][0]["district"], "Srinagar")
        resource_id = resources.json()["resources"][0]["resource_id"]
        self.assertEqual(self.client.get(f"/api/resources/{resource_id}").status_code, 200)
        run = self.client.post("/api/predictions", json={"mode": "simulated_demo"})
        self.assertEqual(run.status_code, 200)
        body = run.json()
        self.assertEqual(body["district_count"], 20)
        self.assertEqual(body["source"], "SIMULATED_DEMO_WEATHER fixture")
        self.assertEqual(body["data_freshness"]["status"], "fixed synthetic fixture; not current weather")
        self.assertTrue(all(item["weather_scope"] == "SIMULATED_DEMO_WEATHER" for item in body["district_results"]))
        self.assertTrue(all(len(item["hazards"]) == 6 for item in body["district_results"]))
        for result in body["district_results"]:
            for hazard in result["hazards"]:
                self.assertIn(hazard["alert_level"], {"NORMAL", "WATCH", "ELEVATED", "HIGH"})
                self.assertIn("validation threshold", hazard["alert_reason"])
                self.assertEqual(hazard["alert_status"], "DEVELOPMENT_SIMULATION_NOT_A_GOVERNMENT_WARNING")
                self.assertEqual(hazard["alert_timestamp"], body["created_at"])
                self.assertEqual(hazard["alert_model_version"], "phase7f_v1")
                self.assertEqual(hazard["alert_data_source"], "SIMULATED_DEMO_WEATHER")

    def test_allocation_route_preserves_contract_and_includes_constraints(self) -> None:
        run = self.client.post("/api/predictions", json={"mode": "simulated_demo"}).json()
        plan_response = self.client.get(f"/api/response-plan?run_id={run['id']}")
        self.assertEqual(plan_response.status_code, 200)
        response = self.client.post("/api/allocations/simulate", json={"run_id": run["id"]})
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["status"], "SIMULATION_ONLY_NOT_FOR_DISPATCH")
        self.assertEqual(result["simulation_version"], "phase9_simulation_v1")
        self.assertEqual(result["inventory"]["scope"], "SIMULATED_DEVELOPMENT_ONLY")
        ids = [item["resource_id"] for row in result["allocations"] for item in row["resource_assignments"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(item["estimated_travel_time_minutes"] <= result["max_simulated_travel_minutes"] for row in result["allocations"] for item in row["resource_assignments"]))
        self.assertTrue(all(item["status"] == "unavailable" for item in result["production_input_availability"].values()))

    def test_live_provider_failure_is_contained_to_one_district(self) -> None:
        class Provider:
            def fetch_features(self, district: str, latitude: float, longitude: float) -> dict:
                if district == "Srinagar":
                    raise RuntimeError("isolated simulated provider error")
                result = replay_features(api_main.REPLAY, district)
                result["source"] = "TEST_MOCK_LIVE_PROVIDER"
                result["retrieved_at"] = "2026-09-27T00:00:00+00:00"
                result["weather_scope"] = "TEST_MOCK_LIVE_PROVIDER"
                return result

        with patch.object(api_main, "WEATHER", Provider()):
            response = self.client.post("/api/predictions", json={"mode": "live"})
        self.assertEqual(response.status_code, 200)
        run = response.json()
        self.assertEqual(run["status"], "partial")
        self.assertEqual(run["district_count"], 19)
        srinagar = next(item for item in run["district_results"] if item["district"] == "Srinagar")
        self.assertEqual(srinagar["status"], "unavailable")

    def test_all_weather_failures_return_explicit_unavailable_rows(self) -> None:
        class FailedProvider:
            def fetch_features(self, district: str, latitude: float, longitude: float) -> dict:
                raise RuntimeError("offline")

        with patch.object(api_main, "WEATHER", FailedProvider()):
            response = self.client.post("/api/predictions", json={"mode": "live"})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "unavailable")
        self.assertEqual(body["district_count"], 0)
        self.assertEqual(body["unavailable_district_count"], 20)
        self.assertTrue(all(item["status"] == "unavailable" for item in body["district_results"]))

    def test_oversized_request_body_is_rejected(self) -> None:
        response = self.client.post("/api/predictions", content=b" " * (api_main.MAX_REQUEST_BODY_BYTES + 1), headers={"Content-Type": "application/json"})
        self.assertEqual(response.status_code, 413)


if __name__ == "__main__":
    unittest.main()
