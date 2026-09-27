"""Validate the evidence-only landslide research inventory."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = PROJECT_ROOT / "data" / "raw" / "disasters" / "landslide_inventory.csv"
SOURCES_PATH = PROJECT_ROOT / "data" / "raw" / "disasters" / "landslide_sources.csv"
REPORT_PATH = PROJECT_ROOT / "results" / "landslide_source_summary.csv"
INVENTORY_COLUMNS = [
    "event_id", "event_date", "district", "latitude", "longitude", "location",
    "landslide_type", "trigger", "severity", "impact", "source_name", "source_url",
    "verified", "curation_status", "notes",
]
PROJECT_DISTRICTS = {
    "Jammu", "Srinagar", "Anantnag", "Baramulla", "Kupwara", "Pulwama",
    "Budgam", "Bandipora", "Ganderbal", "Doda", "Kathua", "Udhampur",
    "Rajouri", "Poonch", "Kulgam", "Kishtwar", "Ramban", "Reasi",
    "Samba", "Shopian",
}


def main() -> int:
    inventory = pd.read_csv(INVENTORY_PATH, dtype=str)
    sources = pd.read_csv(SOURCES_PATH, dtype=str)
    if list(inventory.columns) != INVENTORY_COLUMNS:
        raise ValueError("Landslide inventory schema mismatch")
    if inventory["event_id"].duplicated().any():
        raise ValueError("Duplicate event IDs found")
    if inventory.duplicated(subset=["event_date", "latitude", "longitude"], keep=False).any():
        raise ValueError("Duplicate event-date-coordinate records found")
    if not inventory.empty:
        dates = pd.to_datetime(inventory["event_date"], errors="coerce")
        if dates.isna().any():
            raise ValueError("Inventory contains invalid dates")
        if not inventory["district"].isin(PROJECT_DISTRICTS).all():
            raise ValueError("Inventory contains a district outside the project scope")

    summary = pd.read_csv(REPORT_PATH, dtype=str)
    expected = {
        "inventory_records_written": "0",
        "project_district_records": "0",
        "duplicate_event_ids_in_inventory": "0",
        "duplicate_event_date_coordinate_rows": "0",
        "synthetic_records_created": "No",
        "weather_labels_created": "No",
        "weather_files_modified": "No",
        "flood_files_modified": "No",
        "ml_models_trained": "No",
    }
    actual = dict(zip(summary["metric"], summary["value"]))
    for metric, value in expected.items():
        if actual.get(metric) != value:
            raise ValueError(f"Validation metric {metric}={actual.get(metric)!r}; expected {value!r}")

    print("=" * 72)
    print("LANDSLIDE RESEARCH VALIDATION")
    print("=" * 72)
    print(f"Source registry rows: {len(sources)}")
    print(f"Inventory records: {len(inventory)}")
    print("J&K project-period records: 0")
    print("Duplicate event IDs: 0")
    print("Duplicate event-date-coordinate rows: 0")
    print("Synthetic records: No")
    print("Weather labels/files modified: No")
    print("Flood files modified: No")
    print("ML models trained: No")
    print("Decision: INSUFFICIENT — NO VERIFIED PROJECT-PERIOD LANDSLIDE LABEL DATA FOUND")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError) as exc:
        print(f"LANDSLIDE RESEARCH VALIDATION FAILED: {exc}", file=sys.stderr)
        sys.exit(1)