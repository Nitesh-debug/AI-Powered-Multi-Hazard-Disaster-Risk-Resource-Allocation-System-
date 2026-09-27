"""Validate the evidence-only coldwave research inventory."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = PROJECT_ROOT / "data" / "raw" / "disasters" / "coldwave_inventory.csv"
SOURCES_PATH = PROJECT_ROOT / "data" / "raw" / "disasters" / "coldwave_sources.csv"
SUMMARY_PATH = PROJECT_ROOT / "results" / "coldwave_source_summary.csv"
INVENTORY_COLUMNS = [
    "event_id", "event_date", "district", "station", "minimum_temperature_c",
    "normal_minimum_temperature_c", "departure_from_normal_c", "coldwave_classification",
    "severe_coldwave_classification", "severity", "duration_days", "source_name",
    "source_url", "verified", "record_type", "notes",
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
        raise ValueError("Coldwave inventory schema mismatch")
    dates = pd.to_datetime(inventory["event_date"], errors="coerce")
    if dates.notna().any() and dates.isna().any():
        raise ValueError("Inventory contains mixed valid and invalid dates")
    if inventory["event_id"].duplicated().any():
        raise ValueError("Duplicate coldwave event IDs found")
    if inventory.duplicated(subset=["event_date", "station"], keep=False).any():
        raise ValueError("Duplicate event-date-station combinations found")
    if not inventory.empty and not inventory["district"].isin(PROJECT_DISTRICTS).all():
        raise ValueError("Inventory contains a district outside the project scope")

    summary = pd.read_csv(SUMMARY_PATH, dtype=str)
    actual = dict(zip(summary["metric"], summary["value"]))
    expected = {
        "total_candidate_records": "0",
        "jammu_kashmir_records": "0",
        "project_district_records": "0",
        "duplicate_event_ids": "0",
        "duplicate_event_date_station_combinations": "0",
        "synthetic_records_created": "No",
        "weather_derived_labels_created": "No",
        "flood_files_modified": "No",
        "landslide_files_modified": "No",
        "heatwave_files_modified": "No",
        "weather_files_modified": "No",
        "ml_models_trained": "No",
    }
    for metric, value in expected.items():
        if actual.get(metric) != value:
            raise ValueError(f"Validation metric {metric}={actual.get(metric)!r}; expected {value!r}")

    print("=" * 72)
    print("COLDWAVE RESEARCH VALIDATION")
    print("=" * 72)
    print(f"Source registry rows: {len(sources)}")
    print(f"Candidate inventory records: {len(inventory)}")
    print("J&K records: 0")
    print("Project-district records: 0")
    print("Missing dates: 0")
    print("Duplicate event IDs: 0")
    print("Duplicate event-date-station combinations: 0")
    print("Synthetic records/labels: No")
    print("Flood, landslide, heatwave, and weather files modified: No")
    print("ML models trained: No")
    print("Decision: INSUFFICIENT — NO VERIFIED PROJECT-PERIOD COLDWAVE LABEL DATA FOUND")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError) as exc:
        print(f"COLDWAVE RESEARCH VALIDATION FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
