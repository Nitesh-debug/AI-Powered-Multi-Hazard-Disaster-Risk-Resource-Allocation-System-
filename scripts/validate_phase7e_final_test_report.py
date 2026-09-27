"""Validate sealed Phase 7E metrics without opening datasets or model files."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_ROOT = PROJECT_ROOT / "models" / "development" / "phase7e_selected"
METRICS_PATH = PROJECT_ROOT / "results" / "ml" / "phase7e" / "final_test_metrics.csv"
REPORT_PATH = PROJECT_ROOT / "results" / "ml" / "phase7e_final_test_evaluation.md"
HAZARDS = ("flood", "heavy_rain", "landslide", "heatwave", "coldwave", "windstorm")


def validate() -> None:
    metrics = pd.read_csv(METRICS_PATH)
    report = REPORT_PATH.read_text(encoding="utf-8")
    if "SYNTHETIC_DEVELOPMENT_ONLY" not in report or "not be used for real alerts" not in report:
        raise ValueError("The final evaluation report is missing its development-only warning")
    if len(metrics) != len(HAZARDS) * 25:
        raise ValueError(f"Expected 150 overall and support-gated subgroup metric rows, found {len(metrics)}")
    if set(metrics["hazard"].unique()) != set(HAZARDS):
        raise ValueError("Final test report does not cover the six hazards exactly")
    if set(metrics["scope"].unique()) != {"overall", "district", "season"}:
        raise ValueError("Final test report subgroup scopes are incomplete")
    if not metrics["threshold_from_validation"].between(0.1, 0.9).all():
        raise ValueError("A reported threshold is outside the validation-selected search range")

    for hazard in HAZARDS:
        section = metrics.loc[metrics["hazard"].eq(hazard)]
        overall = section.loc[section["scope"].eq("overall")]
        district = section.loc[section["scope"].eq("district")]
        season = section.loc[section["scope"].eq("season")]
        if len(overall) != 1 or len(district) != 20 or len(season) != 4:
            raise ValueError(f"Incorrect overall/district/season output counts for {hazard}")
        row = overall.iloc[0]
        if int(row["rows"]) != 20_700 or row["evaluation_status"] != "evaluated":
            raise ValueError(f"Overall test metric row is incomplete for {hazard}")
        if int(district["rows"].sum()) != 20_700 or int(season["rows"].sum()) != 20_700:
            raise ValueError(f"Subgroup row totals do not cover the test period for {hazard}")

        metadata_path = MODEL_ROOT / hazard / "metadata.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata.get("label_scope") != "SYNTHETIC_DEVELOPMENT_ONLY":
            raise ValueError(f"Synthetic scope missing from selected model metadata for {hazard}")
        if metadata.get("test_data_accessed") is not True or metadata.get("test_evaluation", {}).get("status") != "completed_once":
            raise ValueError(f"One-time evaluation seal missing for {hazard}")
        if metadata.get("test_period", {}).get("evaluation_status") != "completed_once":
            raise ValueError(f"Test period status is stale for {hazard}")
        if not np.isclose(float(metadata["test_metrics"]["average_precision"]), float(row["average_precision"])):
            raise ValueError(f"Recorded overall average precision differs from metadata for {hazard}")
        if metadata["threshold_selection"]["selected_threshold"] != float(row["threshold_from_validation"]):
            raise ValueError(f"Test report appears to have changed the selected threshold for {hazard}")


def main() -> int:
    validate()
    print("PHASE 7E FINAL TEST ARTIFACT VALIDATION: PASS")
    print("Overall metrics: 6; district/season metric rows: 144")
    print("Metadata seals: PASS; validation thresholds preserved: PASS")
    print("Dataset rows/model artifacts opened by this validator: No")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError, AssertionError) as exc:
        print(f"PHASE 7E FINAL TEST ARTIFACT VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
