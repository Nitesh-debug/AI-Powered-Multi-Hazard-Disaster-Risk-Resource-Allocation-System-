import os
import unittest
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["WEATHER_PROVIDER"] = "dummy"

from agents.master_agent import MasterAgent
from scripts.settings import ALLOCATION_SLA_SECONDS, PREDICTION_SLA_SECONDS


class TestAgents(unittest.TestCase):
    def setUp(self):
        self.master = MasterAgent()

    def test_routing_allocation(self):
        response = self.master.process_request("Please run resource allocation for me")
        self.assertEqual(response["agent"], "ResourceAgent")
        self.assertIn("allocation plan generated", response["response_text"].lower())
        self.assertEqual(response["type"], "allocation_plan")
        metrics = response.get("metrics") or {}
        self.assertLess(metrics["prediction_seconds"], PREDICTION_SLA_SECONDS)
        self.assertLess(metrics["allocation_seconds"], ALLOCATION_SLA_SECONDS)

    def test_routing_analytics(self):
        self.master.process_request("run allocation")
        response = self.master.process_request("Show me the risk map")
        self.assertEqual(response["agent"], "AnalyticsAgent")
        self.assertEqual(response["type"], "map_data")
        response_stats = self.master.process_request("Show summary stats")
        self.assertEqual(response_stats["type"], "stats")

    def test_routing_unknown(self):
        response = self.master.process_request("Hello world")
        self.assertEqual(response["agent"], "MasterAgent")
        self.assertIn("Master Disaster Management Agent", response["response_text"])

    def test_demo_allocation(self):
        response = self.master.process_request("Run on demo data")
        self.assertEqual(response["agent"], "ResourceAgent")
        self.assertIn("SIMULATED DEMO DATA", response["response_text"])

    def test_manual_alert(self):
        response = self.master.process_request("Send alert")
        self.assertEqual(response["agent"], "ResourceAgent")
        self.assertTrue(response["type"] in ["alert_confirmation", "info", "error"])

    def test_canonical_outputs(self):
        self.master.process_request("run allocation")
        from storage.database import ALLOCATION_JSON, PREDICTIONS_CSV

        self.assertTrue(PREDICTIONS_CSV.exists())
        self.assertTrue(ALLOCATION_JSON.exists())


if __name__ == "__main__":
    unittest.main()
