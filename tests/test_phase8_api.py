from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
import numpy as np
from fastapi.testclient import TestClient

from api import main as api_main
from api.store import DemoStore
from api.weather import HOURLY_VARIABLES, OpenMeteoFeatureProvider, WeatherUnavailable


class Phase8ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        api_main.STORE = DemoStore(Path(self.temp.name) / "test.sqlite3")
        self.client = TestClient(api_main.app)

    def tearDown(self) -> None:
        self.client.close()
        self.temp.cleanup()

    def test_health_and_replay_prediction_contract(self) -> None:
        health = self.client.get("/api/health")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["scope"], "SYNTHETIC_DEVELOPMENT_ONLY")
        self.assertEqual(health.json()["models_loaded"], 6)
        self.assertEqual(health.json()["model_version"], "phase7f_v1")
        self.assertEqual(health.json()["outbound_notifications"], "disabled for synthetic development outputs")

        response = self.client.post("/api/predictions", json={"mode": "historical_replay"})
        self.assertEqual(response.status_code, 200)
        run = response.json()
        self.assertEqual(run["district_count"], 20)
        self.assertEqual(run["feature_reference_date"], "2025-10-30")
        self.assertEqual(run["target_date"], "2025-10-31")
        self.assertEqual(run["label_scope"], "SYNTHETIC_DEVELOPMENT_ONLY")
        self.assertEqual(run["model_version"], "phase7f_v1")
        self.assertEqual(len(run["district_results"]), 20)
        for result in run["district_results"]:
            self.assertEqual(result["status"], "complete")
            self.assertEqual(len(result["hazards"]), 6)
            self.assertAlmostEqual(
                result["combined_development_risk_score"],
                max(hazard["raw_model_score"] for hazard in result["hazards"]),
            )
            self.assertEqual(result["model_version"], "phase7f_v1")
            self.assertTrue(all(hazard["calibrated_probability"] is False for hazard in result["hazards"]))
            self.assertTrue(all(0.0 <= hazard["raw_model_score"] <= 1.0 for hazard in result["hazards"]))
            self.assertTrue(all("raw uncalibrated estimator score" in hazard["score_semantics"] for hazard in result["hazards"]))
            self.assertTrue(all(hazard["district"] == result["district"] for hazard in result["hazards"]))
            self.assertTrue(all(hazard["target_date"] == run["target_date"] for hazard in result["hazards"]))
            self.assertEqual(
                result["active_hazard_signals"],
                [hazard["hazard"] for hazard in result["hazards"] if hazard["above_validation_threshold"]],
            )
            self.assertTrue(all(hazard["label_scope"] == "SYNTHETIC_DEVELOPMENT_ONLY" for hazard in result["hazards"]))
            self.assertNotIn('"target_label"', json.dumps(result).lower())

    def test_allocation_is_bounded_and_explicitly_simulated(self) -> None:
        run = self.client.post("/api/predictions", json={"mode": "historical_replay"}).json()
        response = self.client.post("/api/allocations", json={"run_id": run["id"]})
        self.assertEqual(response.status_code, 200)
        allocation = response.json()
        self.assertEqual(allocation["status"], "SIMULATION_ONLY_NOT_FOR_DISPATCH")
        self.assertEqual(allocation["inventory"]["scope"], "SIMULATED_DEVELOPMENT_ONLY")
        self.assertTrue(all(
            item["status"] == "unavailable"
            for item in allocation["production_input_availability"].values()
        ))
        assigned = {name: 0 for name in allocation["inventory"]["items"]}
        for row in allocation["allocations"]:
            for name, count in row["simulated_assignment"].items():
                assigned[name] += count
        for name, count in assigned.items():
            self.assertLessEqual(count, allocation["inventory"]["items"][name])
        self.assertEqual(self.client.get("/api/alerts").status_code, 200)

    def test_phase7f_registry_is_versioned_and_development_only(self) -> None:
        response = self.client.get("/api/registry")
        self.assertEqual(response.status_code, 200)
        registry = response.json()
        self.assertEqual(registry["scope"], "SYNTHETIC_DEVELOPMENT_ONLY")
        self.assertEqual(len(registry["hazards"]), 6)
        self.assertTrue(all(item["model_version"] == "phase7f_v1" for item in registry["hazards"]))
        self.assertTrue(all(item["selected_candidate_id"] for item in registry["hazards"]))

    def weather_payload(self, current_date: date, change_future: bool = False) -> dict[str, object]:
        start = datetime.combine(current_date - timedelta(days=8), datetime.min.time(), timezone.utc)
        times = [start + timedelta(hours=hour) for hour in range(10 * 24)]
        hourly: dict[str, list[object]] = {"time": [item.strftime("%Y-%m-%dT%H:%M") for item in times]}
        for name in HOURLY_VARIABLES:
            if name == "weather_code":
                values = [1] * len(times)
            elif name == "relative_humidity_2m":
                values = [55.0] * len(times)
            elif name == "wind_speed_10m":
                values = [8.0] * len(times)
            elif name == "wind_gusts_10m":
                values = [12.0] * len(times)
            elif name.startswith("soil_moisture"):
                values = [0.25] * len(times)
            elif name.startswith("soil_temperature"):
                values = [10.0] * len(times)
            elif name == "snow_depth":
                values = [0.0] * len(times)
            else:
                values = [2.0] * len(times)
            if change_future and name == "temperature_2m":
                values = [999.0 if item.date() >= current_date else value for item, value in zip(times, values)]
            hourly[name] = values
        return {"latitude": 34.0, "longitude": 74.75, "elevation": 1591, "hourly": hourly}

    def test_live_features_are_complete_and_exclude_target_day(self) -> None:
        current_date = datetime.now(ZoneInfo("Asia/Kolkata")).date()
        first = self.weather_payload(current_date)
        second = self.weather_payload(current_date, change_future=True)

        def provider_for(payload: dict[str, object]) -> OpenMeteoFeatureProvider:
            def respond(request: httpx.Request) -> httpx.Response:
                return httpx.Response(200, json=payload)
            return OpenMeteoFeatureProvider(transport=httpx.MockTransport(respond))

        base = provider_for(first).fetch_features("Srinagar", 34.08, 74.80)
        altered = provider_for(second).fetch_features("Srinagar", 34.08, 74.80)
        self.assertEqual(len(base["features"]), 68)
        self.assertEqual(base["feature_reference_date"], (current_date - timedelta(days=1)).isoformat())
        self.assertEqual(base["target_date"], current_date.isoformat())
        self.assertEqual(base["features"], altered["features"])
        self.assertTrue(np.isfinite(np.asarray(list(base["features"].values()), dtype=float)).all())

    def test_live_missing_weather_fails_closed(self) -> None:
        current_date = datetime.now(ZoneInfo("Asia/Kolkata")).date()
        payload = self.weather_payload(current_date)
        payload["hourly"]["soil_moisture_7_to_28cm"][0] = None

        def respond(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=payload)

        provider = OpenMeteoFeatureProvider(transport=httpx.MockTransport(respond))
        with self.assertRaisesRegex(WeatherUnavailable, "missing values are not imputed"):
            provider.fetch_features("Srinagar", 34.08, 74.80)


if __name__ == "__main__":
    unittest.main()
