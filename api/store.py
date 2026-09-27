from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx

from api.config import SQLITE_PATH, SUPABASE_CONFIG_STATE, SUPABASE_ENABLED, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_URL


class DemoStore:
    def __init__(self, path: Path = SQLITE_PATH):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS prediction_runs (
                    id TEXT PRIMARY KEY,
                    mode TEXT NOT NULL,
                    source TEXT NOT NULL,
                    feature_reference_date TEXT NOT NULL,
                    target_date TEXT NOT NULL,
                    label_scope TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS development_alerts (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL REFERENCES prediction_runs(id),
                    district TEXT NOT NULL,
                    hazard TEXT NOT NULL,
                    score REAL NOT NULL,
                    threshold REAL NOT NULL,
                    status TEXT NOT NULL,
                    label_scope TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS allocation_runs (
                    id TEXT PRIMARY KEY,
                    prediction_run_id TEXT NOT NULL REFERENCES prediction_runs(id),
                    inventory_scope TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
            """)

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def save_prediction_run(self, run: dict[str, Any], predictions: list[dict[str, Any]]) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO prediction_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (run["id"], run["mode"], run["source"], run["feature_reference_date"], run["target_date"],
                 run["label_scope"], run["created_at"], json.dumps(run, separators=(",", ":"))),
            )
            for district_result in predictions:
                for hazard in district_result.get("hazards", []):
                    if hazard["above_validation_threshold"]:
                        alert = {
                            "id": f"{run['id']}:{district_result['district']}:{hazard['hazard']}",
                            "run_id": run["id"],
                            "district": district_result["district"],
                            "hazard": hazard["hazard"],
                            "score": hazard["raw_model_score"],
                            "threshold": hazard["validation_threshold_score"],
                            "raw_model_score": hazard["raw_model_score"],
                            "validation_threshold_score": hazard["validation_threshold_score"],
                            "score_semantics": hazard["score_semantics"],
                            "alert_level": hazard["alert_level"],
                            "reason": hazard["alert_reason"],
                            "data_source": hazard["alert_data_source"],
                            "model_version": hazard["model_version"],
                            "target_date": hazard["target_date"],
                            "development_status": "SYNTHETIC_DEVELOPMENT_ONLY_NOT_A_WARNING",
                            "status": "DEVELOPMENT_SIGNAL_NOT_FOR_DISPATCH",
                            "label_scope": run["label_scope"],
                            "created_at": run["created_at"],
                        }
                        connection.execute(
                            "INSERT INTO development_alerts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (alert["id"], alert["run_id"], alert["district"], alert["hazard"], alert["score"],
                             alert["threshold"], alert["status"], alert["label_scope"], alert["created_at"],
                             json.dumps(alert, separators=(",", ":"))),
                        )

    def get_prediction_run(self, run_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute("SELECT payload_json FROM prediction_runs WHERE id=?", (run_id,)).fetchone()
        return json.loads(row["payload_json"]) if row else None

    def save_allocation(self, allocation: dict[str, Any]) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO allocation_runs VALUES (?, ?, ?, ?, ?)",
                (allocation["id"], allocation["prediction_run_id"], allocation["inventory"]["scope"],
                 allocation["created_at"], json.dumps(allocation, separators=(",", ":"))),
            )

    def recent(self, table: str, limit: int = 50) -> list[dict[str, Any]]:
        allowed = {"prediction_runs", "development_alerts", "allocation_runs"}
        if table not in allowed:
            raise ValueError("Unsupported table")
        with self._connect() as connection:
            rows = connection.execute(
                f"SELECT payload_json FROM {table} ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]


class SupabaseMirror:
    def __init__(self):
        self.configured = SUPABASE_ENABLED
        self.enabled = False
        self.status = "not configured; SQLite active" if SUPABASE_CONFIG_STATE == "not_configured" else "partial configuration; SQLite active" if SUPABASE_CONFIG_STATE == "partial" else "configured; schema not checked"

    def check_schema(self) -> bool:
        if not self.configured:
            return False
        parsed_url = urlsplit(SUPABASE_URL)
        if parsed_url.scheme != "https" and parsed_url.hostname not in {"localhost", "127.0.0.1", "::1"}:
            self.status = "configured URL must use HTTPS; SQLite active"
            self.enabled = False
            return False
        if not parsed_url.hostname:
            self.status = "configured URL is invalid; SQLite active"
            self.enabled = False
            return False
        try:
            for table in ("prediction_runs", "development_alerts", "allocation_runs"):
                response = httpx.get(
                    f"{SUPABASE_URL.rstrip('/')}/rest/v1/{table}",
                    params={"select": "id", "limit": 0},
                    headers={"apikey": SUPABASE_SERVICE_ROLE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}"},
                    timeout=4,
                )
                response.raise_for_status()
        except (httpx.HTTPError, ValueError):
            self.status = "configured but connection/schema check failed; SQLite active"
            self.enabled = False
            return False
        self.status = "connected; required tables checked"
        self.enabled = True
        return True

    def mirror(self, table: str, record: dict[str, Any]) -> None:
        if not self.enabled:
            return
        response = httpx.post(
            f"{SUPABASE_URL.rstrip('/')}/rest/v1/{table}",
            params={"on_conflict": "id"},
            headers={
                "apikey": SUPABASE_SERVICE_ROLE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates,return=minimal",
            },
            json=record,
            timeout=10,
        )
        response.raise_for_status()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
