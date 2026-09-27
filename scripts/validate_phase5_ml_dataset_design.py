"""Validate Phase 5 ML dataset design artifacts without changing project data."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DESIGN_MD_PATH = PROJECT_ROOT / "results" / "phase5_ml_dataset_design.md"
FEATURE_SCHEMA_PATH = PROJECT_ROOT / "results" / "phase5_ml_feature_schema.csv"
SPLIT_PLAN_PATH = PROJECT_ROOT / "results" / "phase5_temporal_split_plan.csv"
SUMMARY_PATH = PROJECT_ROOT / "results" / "phase5_ml_dataset_summary.csv"

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

EXPECTED_SPLITS = {
    "train": ("2020-01-02", "2021-12-31", 14_600, 17),
    "validation": ("2022-01-01", "2022-12-31", 7_300, 8),
    "test": ("2023-01-01", "2025-10-31", 20_700, 7),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_summary(summary: pd.DataFrame, metric: str, expected: str) -> None:
    matches = summary.loc[summary["metric"].eq(metric), "value"]
    if matches.empty:
        raise ValueError(f"Missing summary metric: {metric}")
    actual = str(matches.iloc[0])
    if actual != expected:
        raise ValueError(f"Summary metric {metric} is {actual}; expected {expected}")


def main() -> int:
    for path in (DESIGN_MD_PATH, FEATURE_SCHEMA_PATH, SPLIT_PLAN_PATH, SUMMARY_PATH):
        if not path.exists():
            raise ValueError(f"Missing Phase 5 artifact: {path.relative_to(PROJECT_ROOT)}")

    for relative_path, expected_hash in FROZEN_HASHES.items():
        path = PROJECT_ROOT / relative_path
        if not path.exists():
            raise ValueError(f"Frozen artifact missing: {relative_path}")
        if sha256(path) != expected_hash:
            raise ValueError(f"Frozen artifact changed: {relative_path}")

    schema = pd.read_csv(FEATURE_SCHEMA_PATH, dtype=str)
    required_schema_columns = {"source_column", "role", "phase6_baseline_action", "leakage_note"}
    if set(schema.columns) != required_schema_columns:
        raise ValueError("Feature schema columns do not match the Phase 5 contract")
    for column in ("flood_event_label", "label_status", "label_source", "label_source_url", "flood_event_ids"):
        action = schema.loc[schema["source_column"].eq(column), "phase6_baseline_action"]
        if action.empty or action.iloc[0] != "exclude_from_features":
            raise ValueError(f"{column} must be excluded from model features")
    shifted_features = schema["phase6_baseline_action"].str.startswith("shift_by_1_day", na=False).sum()
    if shifted_features != 68:
        raise ValueError(f"Expected 68 shifted baseline feature columns, found {shifted_features}")

    split_plan = pd.read_csv(SPLIT_PLAN_PATH, dtype={"split": str})
    if set(split_plan["split"]) != set(EXPECTED_SPLITS):
        raise ValueError("Temporal split names do not match expected train/validation/test")
    if int(split_plan["district_days"].sum()) != 42_600:
        raise ValueError("Temporal split row count should be 42,600 one-day-lead eligible district-days")
    if int(split_plan["verified_flood_positives"].sum()) != 32:
        raise ValueError("Temporal splits must preserve exactly 32 verified positives")
    if int(split_plan["confirmed_negative_days"].sum()) != 0:
        raise ValueError("Phase 5 must not introduce confirmed negative labels")
    for split, (start, end, rows, positives) in EXPECTED_SPLITS.items():
        item = split_plan.loc[split_plan["split"].eq(split)].iloc[0]
        if item["target_start_date"] != start or item["target_end_date"] != end:
            raise ValueError(f"{split} split date bounds changed")
        if int(item["district_days"]) != rows:
            raise ValueError(f"{split} row count is {item['district_days']}; expected {rows}")
        if int(item["verified_flood_positives"]) != positives:
            raise ValueError(f"{split} positives are {item['verified_flood_positives']}; expected {positives}")
        if item["supervised_binary_ready"] != "No":
            raise ValueError(f"{split} must remain marked not supervised-binary-ready")

    summary = pd.read_csv(SUMMARY_PATH, dtype=str)
    require_summary(summary, "supervised_binary_training_ready", "No")
    require_summary(summary, "synthetic_labels_created", "No")
    require_summary(summary, "processed_data_modified", "No")
    require_summary(summary, "ml_models_trained", "No")
    require_summary(summary, "confirmed_negative_days", "0")

    report_text = DESIGN_MD_PATH.read_text(encoding="utf-8")
    for required_text in (
        "one-day lead",
        "NO_VERIFIED_EVENT",
        "unknown/not established",
        "must not be converted to `0`",
        "Target and provenance fields are excluded",
        "No ML model was trained",
    ):
        if required_text not in report_text:
            raise ValueError(f"Missing required Phase 5 safeguard: {required_text}")

    print("=" * 72)
    print("PHASE 5 ML DATASET DESIGN VALIDATION")
    print("=" * 72)
    print("Design artifacts: PASS")
    print("Frozen raw/processed artifact hashes: PASS")
    print("One-day lead temporal splits: PASS")
    print("Verified flood positives preserved: 32")
    print("Confirmed negatives introduced: 0")
    print("Synthetic labels: No")
    print("Processed data modified: No")
    print("ML models trained: No")
    print("Result: PASS")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, IndexError) as exc:
        print(f"PHASE 5 ML DATASET DESIGN VALIDATION FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
