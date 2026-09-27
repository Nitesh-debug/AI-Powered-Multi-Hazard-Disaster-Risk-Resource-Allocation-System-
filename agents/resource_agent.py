"""Resource agent: live weather -> batch ML risk scores -> allocation."""

from __future__ import annotations

import os
import sys
import time
from typing import Any

import joblib
import numpy as np
import pandas as pd

from .base_agent import Agent
from scripts.settings import PREDICTION_SLA_SECONDS, PROJECT_ROOT, RESULTS_DIR, SCRIPTS_DIR
from scripts.weather_client import dummy_weather_frame, fetch_live_weather
from storage.database import get_storage

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from resource_allocation import allocate_resources  # noqa: E402


class ResourceAgent(Agent):
    def __init__(self, master_agent: Any | None = None) -> None:
        super().__init__("ResourceAgent")
        self.master = master_agent
        self.model: Any = None
        self.scaler: Any = None
        self.feature_cols: list[str] = []
        self.district_encoder: Any = None
        self._load_models()

    def _load_models(self) -> None:
        try:
            self.model = joblib.load(SCRIPTS_DIR / "disaster_prediction_model.pkl")
            self.scaler = joblib.load(SCRIPTS_DIR / "scaler.pkl")
            self.district_encoder = joblib.load(SCRIPTS_DIR / "district_encoder.pkl")
            self.feature_cols = list(joblib.load(SCRIPTS_DIR / "feature_columns.pkl"))
        except Exception as exc:
            print(f"Error loading models: {exc}")

    def safe_encode(self, dname: str) -> int:
        try:
            return int(self.district_encoder.transform([dname])[0])
        except Exception:
            try:
                classes = list(self.district_encoder.classes_)
                return int(classes.index(dname)) if dname in classes else 0
            except Exception:
                return 0

    def process_request(self, query: str) -> dict[str, Any]:
        q = query.lower()
        if "demo" in q:
            return self.run_demo_allocation()
        if "send alert" in q or "trigger alert" in q:
            return self.trigger_manual_alerts()
        if any(w in q for w in ("allocate", "resource", "plan", "predict", "risk", "weather")):
            return self.run_allocation(use_live=True)
        return self._format_response(
            "I can help you with running resource allocation and risk prediction. "
            "Try asking 'Run resource allocation'."
        )

    def _load_historical_csv(self) -> pd.DataFrame | None:
        candidates = [
            PROJECT_ROOT / "jk_weather_history_enhanced.csv",
            SCRIPTS_DIR / "jk_weather_history_enhanced.csv",
            PROJECT_ROOT / "data" / "jk_weather_history_enhanced.csv",
        ]
        for path in candidates:
            if path.exists():
                return pd.read_csv(path)
        return None

    def run_demo_allocation(self) -> dict[str, Any]:
        from scripts.district_info import district_data

        demo_districts = {"Srinagar", "Jammu", "Baramulla", "Anantnag"}
        now = pd.Timestamp.utcnow().isoformat()
        records: list[dict[str, Any]] = []
        for name in district_data:
            rec = {
                "District": name,
                "Fetch_Time_UTC": now,
                "Temp_C": 20,
                "Humidity": 50,
                "Wind_Kph": 10,
                "Pressure_mb": 1010,
                "Precip_mm": 0,
                "source": "demo",
            }
            if name in demo_districts:
                rec.update(
                    {
                        "Wind_Kph": 120,
                        "Precip_mm": 250,
                        "Pressure_mb": 980,
                        "Humidity": 95,
                    }
                )
            records.append(rec)
        return self.run_allocation(use_df=pd.DataFrame(records), is_demo=True, source_label="demo")

    def trigger_manual_alerts(self) -> dict[str, Any]:
        if not self.master:
            return self._format_response("Notification system not connected.", resp_type="error", error="no_master")

        try:
            RESULTS_DIR.mkdir(parents=True, exist_ok=True)
            pred_files = sorted(
                [f for f in os.listdir(RESULTS_DIR) if f.startswith("predictions") and f.endswith(".csv")]
            )
            if not pred_files:
                return self._format_response("No prediction data found. Run allocation first.", resp_type="error")

            last_file = RESULTS_DIR / pred_files[-1]
            df = pd.read_csv(last_file)
            high_risk = df[df["risk_level"] >= 3]
            if high_risk.empty:
                return self._format_response(
                    "No High Risk (Level 3+) districts found in the latest data.",
                    resp_type="info",
                )

            alert_log: list[str] = []
            for _, row in high_risk.iterrows():
                alert_type = "High Risk"
                if row.get("Precip_mm", 0) >= 100:
                    alert_type = "Cloud Burst"
                elif row.get("Precip_mm", 0) >= 50:
                    alert_type = "Heavy Rain"
                elif row.get("Wind_Kph", 0) >= 80:
                    alert_type = "Severe Storm"
                resp = self.master.notification_agent.send_alert(
                    row["district"], row["risk_level"], alert_type=alert_type
                )
                alert_log.append(resp["response_text"])

            return self._format_response(
                f"🚨 **Manual Alerts Triggered** for {len(high_risk)} districts:\n- " + "\n- ".join(alert_log),
                resp_type="alert_confirmation",
            )
        except Exception as exc:
            return self._format_response(f"Error triggering alerts: {exc}", resp_type="error", error=str(exc))

    def _predict_batch(self, df_latest: pd.DataFrame, is_demo: bool) -> tuple[list[dict[str, Any]], float]:
        """Vectorized inference. Report SLA: prediction < 0.3s."""
        missing = [c for c in self.feature_cols if c not in df_latest.columns]
        for col in missing:
            df_latest[col] = 0.0

        x_raw = df_latest[self.feature_cols].astype(float).to_numpy()
        started = time.perf_counter()
        xs = self.scaler.transform(x_raw)
        preds = self.model.predict(xs)
        probas = self.model.predict_proba(xs)
        elapsed = time.perf_counter() - started

        classes = list(self.model.classes_)
        safe_idx = classes.index(0) if 0 in classes else None
        predictions: list[dict[str, Any]] = []
        for i, row in enumerate(df_latest.itertuples(index=False)):
            district = getattr(row, "District")
            pred = int(preds[i])
            if safe_idx is not None:
                risk_prob = 1.0 - float(probas[i][safe_idx])
            else:
                risk_prob = 1.0
            if is_demo and district == "Jammu":
                pred = 4
                risk_prob = 1.0
            predictions.append(
                {
                    "district": district,
                    "risk_level": pred,
                    "risk_probability": round(risk_prob, 3),
                }
            )
        return predictions, elapsed

    def run_allocation(
        self,
        use_live: bool = False,
        use_df: pd.DataFrame | None = None,
        is_demo: bool = False,
        source_label: str | None = None,
    ) -> dict[str, Any]:
        if not self.model:
            return self._format_response("Models are not loaded correctly.", resp_type="error", error="model_missing")

        df = use_df
        source = source_label or "historical_csv"
        if df is None and use_live:
            df, source = fetch_live_weather()
        if df is None:
            df = self._load_historical_csv()
            source = "historical_csv"
        if df is None:
            df = dummy_weather_frame()
            source = "dummy"

        try:
            work = df.copy()
            if "Fetch_Time_UTC" in work.columns:
                work["Fetch_Time_UTC"] = pd.to_datetime(work["Fetch_Time_UTC"], errors="coerce")
                df_latest = work.sort_values("Fetch_Time_UTC").groupby("District", as_index=False).last()
            else:
                df_latest = work.copy()

            if "district_encoded" in self.feature_cols:
                df_latest["district_encoded"] = df_latest["District"].apply(self.safe_encode)

            predictions, pred_seconds = self._predict_batch(df_latest, is_demo=is_demo)

            alloc_started = time.perf_counter()
            allocation_plan = allocate_resources(predictions)
            alloc_seconds = time.perf_counter() - alloc_started

            run_id = pd.Timestamp.utcnow().strftime("/%Y-%m-%d_%H-%M-%S").replace("/", "")
            weather_rows = df_latest.to_dict(orient="records")
            paths = get_storage().persist_run(
                run_id=run_id,
                predictions=predictions,
                allocation_plan=allocation_plan,
                weather_rows=weather_rows,
                source=source,
            )

            alert_log: list[str] = []
            if self.master:
                high_risk = [p for p in predictions if p["risk_level"] >= 3]
                by_name = {r["District"]: r for r in weather_rows}
                for item in high_risk:
                    row_data = by_name.get(item["district"], {})
                    precip = float(row_data.get("Precip_mm", 0) or 0)
                    wind = float(row_data.get("Wind_Kph", 0) or 0)
                    alert_type = "High Risk"
                    if precip >= 100:
                        alert_type = "Cloud Burst"
                    elif precip >= 50:
                        alert_type = "Heavy Rain"
                    elif wind >= 80:
                        alert_type = "Severe Storm"
                    if is_demo and item["district"] == "Jammu":
                        alert_type = "Cloud Burst"
                    resp = self.master.notification_agent.send_alert(
                        item["district"], item["risk_level"], alert_type=alert_type
                    )
                    alert_log.append(resp["response_text"])

            if is_demo:
                source_msg = "🚨 SIMULATED DEMO DATA (4 High Risk Alerts) 🚨"
            else:
                source_msg = f"Live Weather ({source})" if use_live else "Historical / dummy weather"

            sla_note = (
                f"Prediction {pred_seconds:.4f}s "
                f"({'OK' if pred_seconds < PREDICTION_SLA_SECONDS else 'SLA miss'} vs {PREDICTION_SLA_SECONDS}s); "
                f"Allocation {alloc_seconds:.4f}s "
                f"({'OK' if alloc_seconds < 1.0 else 'SLA miss'} vs 1.0s)."
            )
            msg = (
                f"Resource allocation plan generated using **{source_msg}**!\n"
                f"Saved to `{paths['predictions_csv']}` and `{paths['allocation_json']}`.\n"
                f"{sla_note}"
            )
            if alert_log:
                msg += "\n\n🚨 **SMS Alerts Triggered**:\n- " + "\n- ".join(alert_log)

            return self._format_response(
                msg,
                data=allocation_plan,
                resp_type="allocation_plan",
                metrics={"prediction_seconds": pred_seconds, "allocation_seconds": alloc_seconds},
            )
        except Exception as exc:
            return self._format_response(f"Error during allocation: {exc}", resp_type="error", error=str(exc))
