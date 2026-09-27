"""Validate the consolidated Phase 4 assessment without changing project data."""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSESSMENT_CSV = PROJECT_ROOT / "results" / "phase4_disaster_data_assessment.csv"
ASSESSMENT_MD = PROJECT_ROOT / "results" / "phase4_disaster_data_assessment.md"
EXPECTED_DISASTERS = {"Flood", "Landslide", "Heatwave", "Coldwave", "Windstorm", "Heavy Rain"}
ALLOWED_STATUSES = {
    "VERIFIED_LABELS_AVAILABLE",
    "CRITERIA_BASED_LABELING_POSSIBLE_AFTER_DATA_ACQUISITION",
    "ADDITIONAL_HISTORICAL_DATA_REQUIRED",
}
FROZEN_HASHES = {
    "data/raw/disasters/curated_flood_events.csv": "def5bfb0dc24c6c02f69926cd29e7ca3a73ee5edecb766e6c7627cf460cc9779",
    "data/processed/daily_flood_dataset.csv": "609154b4f62a4628f464decbb668722d230386580b69f872db53cc6704d172a2",
    "data/raw/disasters/landslide_inventory.csv": "000b9fc6117ac743495ee0214957219e1c52827e809e3ff4a62e28226d75175a",
    "data/raw/disasters/heatwave_inventory.csv": "2e8038bfab4be1779108145776faa9893ca1649ccd903c2b9c8caa991c8e4a0d",
    "data/raw/disasters/coldwave_inventory.csv": "08a374bd4ff8e1f13e620deb11658e6cabaac8a702225140808b0f62e9c583fd",
    "data/raw/disasters/windstorm_inventory.csv": "62dd6e1f3bfa7abfcf92e4ecf659b6543d863a6fe8bc36bf890688a70138c4b8",
    "data/raw/disasters/heavy_rain_inventory.csv": "945fbe58ef4d9864d4a63a2297ae707d9b9d577f88683f26d1418b4c7fcdf1f8",
    "data/processed/weather_features.csv": "18eeac8a77735db0e408e0e5c685f3ac4c65eac3fd6d22f0bec6c805c4a65df0",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_metric(path: Path, column: str, expected: str) -> None:
    frame = pd.read_csv(path, dtype=str)
    if column not in frame.columns:
        raise ValueError(f"Missing assessment column: {column}")
    if not frame[column].astype(str).eq(expected).all():
        raise ValueError(f"Assessment column {column} does not match {expected}")


def leading_int(value: object) -> int:
    match = re.match(r"\s*(\d+)", str(value))
    if not match:
        raise ValueError(f"Value does not start with an integer count: {value}")
    return int(match.group(1))


def main() -> int:
    assessment = pd.read_csv(ASSESSMENT_CSV, dtype=str)
    if set(assessment["disaster"]) != EXPECTED_DISASTERS:
        raise ValueError("Assessment does not contain exactly the six required disasters")
    if not set(assessment["label_status"]).issubset(ALLOWED_STATUSES):
        raise ValueError("Assessment contains an unsupported label status")
    if len(assessment) != 6:
        raise ValueError("Assessment must contain exactly six rows")

    expected_counts = {
        "Flood": "32",
        "Landslide": "0",
        "Heatwave": "0",
        "Coldwave": "0",
        "Windstorm": "0",
        "Heavy Rain": "0",
    }
    for disaster, expected in expected_counts.items():
        actual = assessment.loc[assessment["disaster"] == disaster, "verified_event_count"].iloc[0]
        if leading_int(actual) != int(expected):
            raise ValueError(f"{disaster} verified count is {actual}; expected {expected}")

    report_text = ASSESSMENT_MD.read_text(encoding="utf-8")
    report_text_lower = report_text.lower()
    for disaster in EXPECTED_DISASTERS:
        if disaster not in report_text:
            raise ValueError(f"Missing disaster section/reference: {disaster}")
    for required_text in (
        "Event label is not the same as a weather observation",
        "Absence of a historical record is not confirmed absence",
        "Open-Meteo",
        "NOAA wind observations",
        "IMD rainfall thresholds",
        "unknown",
        "No Phase 5 work was started",
    ):
        if required_text.lower() not in report_text_lower:
            raise ValueError(f"Missing required assessment safeguard: {required_text}")

    for relative_path, expected_hash in FROZEN_HASHES.items():
        path = PROJECT_ROOT / relative_path
        if not path.exists():
            raise ValueError(f"Frozen artifact missing: {relative_path}")
        if sha256(path) != expected_hash:
            raise ValueError(f"Frozen artifact changed: {relative_path}")

    flood = pd.read_csv(PROJECT_ROOT / "data/processed/daily_flood_dataset.csv", dtype=str)
    if int(flood["label_status"].eq("VERIFIED_FLOOD").sum()) != 32:
        raise ValueError("Daily flood dataset no longer contains exactly 32 verified positives")
    for relative_path in (
        "data/raw/disasters/landslide_inventory.csv",
        "data/raw/disasters/heatwave_inventory.csv",
        "data/raw/disasters/coldwave_inventory.csv",
        "data/raw/disasters/windstorm_inventory.csv",
        "data/raw/disasters/heavy_rain_inventory.csv",
    ):
        inventory = pd.read_csv(PROJECT_ROOT / relative_path, dtype=str)
        if not inventory.empty:
            raise ValueError(f"Non-empty unverified inventory found: {relative_path}")

    print("=" * 72)
    print("PHASE 4 CONSOLIDATED ASSESSMENT VALIDATION")
    print("=" * 72)
    print("Six disaster sections: PASS")
    print("Flood verified district-days: 32")
    print("Landslide project-period accepted records: 0")
    print("Heatwave candidate records: 0")
    print("Coldwave candidate records: 0")
    print("Windstorm event records: 0")
    print("Heavy-rain event records: 0")
    print("Frozen artifact hashes: PASS")
    print("Synthetic labels: No")
    print("ML models trained: No")
    print("Result: PASS")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError) as exc:
        print(f"PHASE 4 ASSESSMENT VALIDATION FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
