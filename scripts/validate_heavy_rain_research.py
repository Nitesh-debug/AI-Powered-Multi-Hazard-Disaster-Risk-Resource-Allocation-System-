"""Validate the evidence-only heavy-rain research inventory."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = PROJECT_ROOT / "data" / "raw" / "disasters" / "heavy_rain_inventory.csv"
SOURCES_PATH = PROJECT_ROOT / "data" / "raw" / "disasters" / "heavy_rain_sources.csv"
SUMMARY_PATH = PROJECT_ROOT / "results" / "heavy_rain_source_summary.csv"
INVENTORY_COLUMNS = [
    "event_id", "event_date", "event_time", "district", "station", "station_id",
    "rainfall_amount_mm", "rainfall_window", "official_classification", "event_type",
    "severity", "impacts", "source_name", "source_url", "verified", "record_type", "notes",
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
        raise ValueError("Heavy-rain inventory schema mismatch")
    dates = pd.to_datetime(inventory["event_date"], errors="coerce")
    if dates.notna().any() and dates.isna().any():
        raise ValueError("Inventory contains mixed valid and invalid dates")
    if inventory["event_id"].duplicated().any():
        raise ValueError("Duplicate heavy-rain event IDs found")
    if inventory.duplicated(subset=["event_date", "station"], keep=False).any():
        raise ValueError("Duplicate event-date-station combinations found")
    if not inventory.empty and not inventory["district"].isin(PROJECT_DISTRICTS).all():
        raise ValueError("Inventory contains a district outside the project scope")

    summary = pd.read_csv(SUMMARY_PATH, dtype=str)
    actual = dict(zip(summary["metric"], summary["value"]))
    expected = {
        "total_candidate_event_records": "0",
        "jammu_kashmir_event_records": "0",
        "project_district_event_records": "0",
        "duplicate_event_ids": "0",
        "duplicate_event_date_station_combinations": "0",
        "synthetic_records_created": "No",
        "weather_derived_labels_created": "No",
        "flood_files_modified": "No",
        "landslide_files_modified": "No",
        "heatwave_files_modified": "No",
        "coldwave_files_modified": "No",
        "windstorm_files_modified": "No",
        "weather_files_modified": "No",
        "ml_models_trained": "No",
    }
    for metric, value in expected.items():
        if actual.get(metric) != value:
            raise ValueError(f"Validation metric {metric}={actual.get(metric)!r}; expected {value!r}")

    print("=" * 72)
    print("HEAVY-RAIN RESEARCH VALIDATION")
    print("=" * 72)
    print(f"Source registry rows: {len(sources)}")
    print(f"Candidate event records: {len(inventory)}")
    print("J&K event records: 0")
    print("Project-district event records: 0")
    print("Duplicate event IDs: 0")
    print("Duplicate event-date-station combinations: 0")
    print("Synthetic records/labels: No")
    print("Flood, landslide, heatwave, coldwave, windstorm, and weather files modified: No")
    print("ML models trained: No")
    print("Decision: PARTIALLY SUFFICIENT — NEED CURATION / OFFICIAL CRITERIA APPLICATION")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError) as exc:
        print(f"HEAVY-RAIN RESEARCH VALIDATION FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
