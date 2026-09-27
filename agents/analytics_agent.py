"""Analytics agent: latest predictions, stats, heatmap payloads, hospitals."""

from __future__ import annotations

import json
from typing import Any

import pandas as pd

from .base_agent import Agent
from scripts.settings import RESULTS_DIR
from storage.database import ALLOCATION_JSON, PREDICTIONS_CSV


class AnalyticsAgent(Agent):
    def __init__(self) -> None:
        super().__init__("AnalyticsAgent")
        self.results_dir = RESULTS_DIR

    def process_request(self, query: str) -> dict[str, Any]:
        q = query.lower()
        if "heatmap" in q or "map" in q:
            return self.get_map_data()
        if any(w in q for w in ("chart", "graph", "stat", "summary")):
            return self.get_summary_stats()
        if "direction" in q or "hospital" in q:
            return self.get_hospital_directions()
        return self._format_response(
            "I can show you the disaster risk map, summary statistics, or hospital directions. "
            "Try 'Show map', 'Show heatmap', 'Show stats', or 'Show directions'."
        )

    def get_latest_results(self) -> pd.DataFrame | None:
        if PREDICTIONS_CSV.exists():
            return pd.read_csv(PREDICTIONS_CSV)
        if not self.results_dir.exists():
            return None
        pred_files = sorted(
            [p for p in self.results_dir.iterdir() if p.name.startswith("predictions") and p.suffix == ".csv"]
        )
        if not pred_files:
            return None
        return pd.read_csv(pred_files[-1])

    def _latest_allocation(self) -> list[dict[str, Any]]:
        if ALLOCATION_JSON.exists():
            return json.loads(ALLOCATION_JSON.read_text(encoding="utf-8"))
        if not self.results_dir.exists():
            return []
        alloc_files = sorted(
            [p for p in self.results_dir.iterdir() if p.name.startswith("allocation") and p.suffix == ".json"]
        )
        if not alloc_files:
            return []
        return json.loads(alloc_files[-1].read_text(encoding="utf-8"))

    def get_map_data(self) -> dict[str, Any]:
        df = self.get_latest_results()
        if df is None:
            return self._format_response("No prediction data found. Please run allocation first.", resp_type="error")
        return self._format_response(
            "Here is the latest disaster risk map configuration.",
            data=df.to_dict(orient="records"),
            resp_type="map_data",
        )

    def get_summary_stats(self) -> dict[str, Any]:
        df = self.get_latest_results()
        if df is None:
            return self._format_response("No prediction data found. Please run allocation first.", resp_type="error")

        high = int((df["risk_level"] >= 3).sum())
        medium = int((df["risk_level"] == 2).sum())
        low = int((df["risk_level"] == 1).sum())
        safe = int((df["risk_level"] == 0).sum())
        stats = {
            "High Risk": high,
            "Medium Risk": medium,
            "Low Risk": low,
            "Safe": safe,
            "Total": len(df),
        }
        return self._format_response(
            f"Summary Stats:\n- High Risk: {high}\n- Medium Risk: {medium}\n- Low Risk: {low}\n- Safe: {safe}",
            data=stats,
            resp_type="stats",
        )

    def get_hospital_directions(self) -> dict[str, Any]:
        df = self.get_latest_results()
        if df is None:
            return self._format_response("No prediction data found. Please run allocation first.", resp_type="error")

        hospitals = {
            "Srinagar": "SKIMS, Soura",
            "Jammu": "GMC Jammu",
            "Anantnag": "GMC Anantnag",
            "Baramulla": "GMC Baramulla",
            "Pulwama": "District Hospital Pulwama",
            "Budgam": "District Hospital Budgam",
            "Kupwara": "District Hospital Kupwara",
            "Kulgam": "District Hospital Kulgam",
            "Shopian": "District Hospital Shopian",
            "Ganderbal": "District Hospital Ganderbal",
            "Bandipora": "District Hospital Bandipora",
            "Kathua": "GMC Kathua",
            "Samba": "District Hospital Samba",
            "Udhampur": "District Hospital Udhampur",
            "Reasi": "District Hospital Reasi",
            "Ramban": "District Hospital Ramban",
            "Doda": "GMC Doda",
            "Kishtwar": "District Hospital Kishtwar",
            "Poonch": "District Hospital Poonch",
            "Rajouri": "GMC Rajouri",
        }

        high_risk_df = df[df["risk_level"] >= 3]
        if high_risk_df.empty:
            return self._format_response("No High Risk areas detected at the moment. No immediate hospital directions needed.")

        directions: list[dict[str, str]] = []
        for _, row in high_risk_df.iterrows():
            district = row["district"]
            hospital = hospitals.get(district, f"General Hospital, {district}")
            query = f"{hospital}, {district}".replace(" ", "+")
            directions.append(
                {
                    "district": district,
                    "hospital": hospital,
                    "link": f"https://www.google.com/maps/search/?api=1&query={query}",
                }
            )
        return self._format_response(
            "Found High Risk areas. Here are the directions to the nearest hospitals:",
            data=directions,
            resp_type="hospital_directions",
        )

    def get_dashboard_summary(self) -> dict[str, Any] | None:
        df = self.get_latest_results()
        if df is None:
            return None

        alloc_data = self._latest_allocation()
        high_risk = df[df["risk_level"] >= 3].to_dict(orient="records")
        medium_risk = df[df["risk_level"] == 2].to_dict(orient="records")
        stats = {
            "total_districts": len(df),
            "high_risk": len(high_risk),
            "medium_risk": len(medium_risk),
            "low_risk": int((df["risk_level"] == 1).sum()),
        }
        stamp = "Unknown"
        if PREDICTIONS_CSV.exists():
            stamp = pd.Timestamp.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        alloc_files = sorted(self.results_dir.glob("allocation_*.json")) if self.results_dir.exists() else []
        if alloc_files:
            stamp = self._extract_timestamp(alloc_files[-1].name)

        return {
            "stats": stats,
            "alerts": high_risk,
            "warnings": medium_risk,
            "map_data": df.to_dict(orient="records"),
            "allocations": alloc_data,
            "last_updated": stamp,
        }

    def _extract_timestamp(self, filename: str) -> str:
        try:
            return filename.replace("allocation_", "").replace(".json", "").replace("_", " ")
        except Exception:
            return "Unknown"
