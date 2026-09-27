"""SQLite persistence with optional Supabase mirroring."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from scripts.settings import RESULTS_DIR, StorageConfig, storage_config

PREDICTIONS_CSV = RESULTS_DIR / "predictions.csv"
ALLOCATION_JSON = RESULTS_DIR / "allocation.json"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    district TEXT NOT NULL,
    risk_level INTEGER NOT NULL,
    risk_probability REAL NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS allocations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS weather_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    district TEXT NOT NULL,
    temp_c REAL,
    humidity REAL,
    wind_kph REAL,
    pressure_mb REAL,
    precip_mm REAL,
    source TEXT,
    created_at TEXT NOT NULL
);
"""


class StorageService:
    """Local SQLite store. Mirrors rows to Supabase when credentials exist."""

    def __init__(self, config: StorageConfig | None = None) -> None:
        self.config = config or storage_config()
        self.config.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        self._init_sqlite()
        self._supabase = self._init_supabase()

    def _init_sqlite(self) -> None:
        with sqlite3.connect(self.config.sqlite_path) as conn:
            conn.executescript(SCHEMA_SQL)

    def _init_supabase(self) -> Any:
        if not self.config.supabase_url or not self.config.supabase_key:
            return None
        try:
            from supabase import create_client

            return create_client(self.config.supabase_url, self.config.supabase_key)
        except Exception as exc:  # pragma: no cover - optional cloud path
            print(f"Supabase client not initialized ({exc}). Using SQLite only.")
            return None

    def persist_run(
        self,
        run_id: str,
        predictions: list[dict[str, Any]],
        allocation_plan: list[dict[str, Any]],
        weather_rows: list[dict[str, Any]] | None = None,
        source: str = "unknown",
    ) -> dict[str, Path]:
        created_at = datetime.now(timezone.utc).isoformat()
        self._write_sqlite(run_id, created_at, predictions, allocation_plan, weather_rows or [], source)
        self._write_files(run_id, predictions, allocation_plan)
        self._write_supabase(run_id, created_at, predictions, allocation_plan)
        return {
            "predictions_csv": PREDICTIONS_CSV,
            "allocation_json": ALLOCATION_JSON,
        }

    def _write_sqlite(
        self,
        run_id: str,
        created_at: str,
        predictions: list[dict[str, Any]],
        allocation_plan: list[dict[str, Any]],
        weather_rows: list[dict[str, Any]],
        source: str,
    ) -> None:
        with sqlite3.connect(self.config.sqlite_path) as conn:
            conn.executemany(
                """
                INSERT INTO predictions (run_id, district, risk_level, risk_probability, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (
                        run_id,
                        row["district"],
                        int(row["risk_level"]),
                        float(row["risk_probability"]),
                        created_at,
                    )
                    for row in predictions
                ],
            )
            conn.execute(
                "INSERT INTO allocations (run_id, payload_json, created_at) VALUES (?, ?, ?)",
                (run_id, json.dumps(allocation_plan), created_at),
            )
            if weather_rows:
                conn.executemany(
                    """
                    INSERT INTO weather_snapshots
                    (run_id, district, temp_c, humidity, wind_kph, pressure_mb, precip_mm, source, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            run_id,
                            row.get("District") or row.get("district"),
                            row.get("Temp_C"),
                            row.get("Humidity"),
                            row.get("Wind_Kph"),
                            row.get("Pressure_mb"),
                            row.get("Precip_mm"),
                            source,
                            created_at,
                        )
                        for row in weather_rows
                    ],
                )
            conn.commit()

    def _write_files(
        self,
        run_id: str,
        predictions: list[dict[str, Any]],
        allocation_plan: list[dict[str, Any]],
    ) -> None:
        import pandas as pd

        pred_df = pd.DataFrame(predictions)
        pred_df.to_csv(PREDICTIONS_CSV, index=False)
        pred_df.to_csv(RESULTS_DIR / f"predictions_{run_id}.csv", index=False)
        payload = json.dumps(allocation_plan, indent=2)
        ALLOCATION_JSON.write_text(payload, encoding="utf-8")
        (RESULTS_DIR / f"allocation_{run_id}.json").write_text(payload, encoding="utf-8")

    def _write_supabase(
        self,
        run_id: str,
        created_at: str,
        predictions: list[dict[str, Any]],
        allocation_plan: list[dict[str, Any]],
    ) -> None:
        if self._supabase is None:
            return
        try:
            self._supabase.table("predictions").insert(
                [
                    {
                        "run_id": run_id,
                        "district": row["district"],
                        "risk_level": int(row["risk_level"]),
                        "risk_probability": float(row["risk_probability"]),
                        "created_at": created_at,
                    }
                    for row in predictions
                ]
            ).execute()
            self._supabase.table("allocations").insert(
                {
                    "run_id": run_id,
                    "payload_json": allocation_plan,
                    "created_at": created_at,
                }
            ).execute()
        except Exception as exc:  # pragma: no cover
            print(f"Supabase write skipped: {exc}")


_storage: StorageService | None = None


def get_storage() -> StorageService:
    global _storage
    if _storage is None:
        _storage = StorageService()
    return _storage
