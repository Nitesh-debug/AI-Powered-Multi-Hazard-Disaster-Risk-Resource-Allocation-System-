"""Validate sealed Phase 7F test metrics without reopening data or models."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import tune_phase7f_models as tuning
import train_phase7d_baselines as phase7d
from evaluate_phase7f_final_test import METRICS_PATH, REPORT_PATH, TEST_ATTEMPT_PATH


def validate() -> None:
    metrics = pd.read_csv(METRICS_PATH)
    report = REPORT_PATH.read_text(encoding="utf-8")
    attempt = json.loads(TEST_ATTEMPT_PATH.read_text(encoding="utf-8"))
    selection = json.loads(tuning.SELECTION_PATH.read_text(encoding="utf-8"))
    if "SYNTHETIC_DEVELOPMENT_ONLY" not in report or "not an independent project-wide pristine holdout" not in report:
        raise ValueError("Test report is missing the synthetic/previous-test-access caveat")
    if attempt.get("status") != "completed_once" or attempt.get("test_data_accessed") is not True:
        raise ValueError("One-time Phase 7F test attempt is not sealed as complete")
    if selection.get("test_data_accessed") is not False:
        raise ValueError("Selection metadata indicates test-based model selection")
    expected_hazards = set(phase7d.HAZARDS.values())
    if len(metrics) != len(expected_hazards) * 25 or set(metrics.hazard.unique()) != expected_hazards:
        raise ValueError("Overall and subgroup metric matrix is incomplete")
    if set(metrics.scope.unique()) != {"overall", "district", "season"}:
        raise ValueError("Expected overall, district and season metric scopes")
    if not metrics.threshold_from_validation.between(0.1, 0.9).all():
        raise ValueError("A reported threshold is outside the validation threshold grid")

    for target, hazard in phase7d.HAZARDS.items():
        subset = metrics.loc[metrics.hazard.eq(hazard)]
        overall = subset.loc[subset.scope.eq("overall")]
        district = subset.loc[subset.scope.eq("district")]
        season = subset.loc[subset.scope.eq("season")]
        if len(overall) != 1 or len(district) != 20 or len(season) != 4:
            raise ValueError(f"Subgroup counts are incorrect for {hazard}")
        row = overall.iloc[0]
        if int(row.rows) != 20_700 or row.evaluation_status != "evaluated":
            raise ValueError(f"Overall metric support is invalid for {hazard}")
        if int(district.rows.sum()) != 20_700 or int(season.rows.sum()) != 20_700:
            raise ValueError(f"District/season supports do not cover test rows for {hazard}")
        if not np.isclose(float(row.threshold_from_validation), float(selection["selected"][hazard]["threshold"])):
            raise ValueError(f"Validation threshold changed during test evaluation for {hazard}")
        metadata = json.loads((tuning.MODEL_ROOT / hazard / "metadata.json").read_text(encoding="utf-8"))
        if metadata.get("label_scope") != tuning.LABEL_SCOPE or metadata.get("label_version") != tuning.LABEL_VERSION:
            raise ValueError(f"Synthetic label metadata mismatch for {hazard}")
        if metadata.get("test_data_accessed") is not True or metadata.get("test_evaluation", {}).get("status") != "completed_once":
            raise ValueError(f"Model test-evaluation seal missing for {hazard}")
        if metadata.get("test_period", {}).get("evaluation_status") != "completed_once":
            raise ValueError(f"Model test period status is stale for {hazard}")
        if not np.isclose(float(metadata["test_metrics"]["average_precision"]), float(row.average_precision)):
            raise ValueError(f"Model metadata AP differs from report for {hazard}")
        if not np.isclose(float(metadata["test_metrics"]["brier_score_raw_score_diagnostic"]), float(row.brier_score_raw_score_diagnostic)):
            raise ValueError(f"Model metadata raw-score Brier diagnostic differs for {hazard}")
        if metadata.get("model_sha256") is None or metadata.get("calibration", {}).get("calibrated") is not False:
            raise ValueError(f"Model identity/calibration metadata invalid for {hazard}")


def main() -> int:
    validate()
    print("PHASE 7F FINAL TEST REPORT VALIDATION: PASS")
    print("Overall metrics: 6; district/season rows: 144")
    print("Frozen validation thresholds and model metadata seals: PASS")
    print("Dataset rows/model artifacts opened by this validator: No")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError, AssertionError) as exc:
        print(f"PHASE 7F FINAL TEST REPORT VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
