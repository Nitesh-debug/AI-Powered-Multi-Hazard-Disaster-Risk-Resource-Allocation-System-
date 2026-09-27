"""Validate frozen Phase 7F selection without opening test rows."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import tune_phase7f_models as tuning
import train_phase7d_baselines as phase7d


def validate() -> dict[str, object]:
    candidates = pd.read_csv(tuning.CANDIDATE_METRICS_PATH)
    thresholds = pd.read_csv(tuning.THRESHOLD_PATH)
    selection = json.loads(tuning.SELECTION_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(tuning.EXPERIMENT_MANIFEST_PATH.read_text(encoding="utf-8"))
    records = [
        json.loads(line)
        for line in tuning.TRIAL_LOG.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    trials = [row for row in records if row.get("event") == "trial_complete"]
    trial_keys = {
        (row.get("hazard"), row.get("algorithm"), int(row.get("trial", 0)))
        for row in trials
    }
    expected_trials = {
        (hazard, algorithm, trial)
        for hazard in tuning.HAZARD_ORDER
        for algorithm in tuning.TUNED_ALGORITHMS
        for trial in range(1, tuning.N_TRIALS + 1)
    }
    expected_candidates = {
        (hazard, candidate)
        for hazard in tuning.HAZARD_ORDER
        for candidate in (
            *[f"phase7d_{name}" for name in tuning.LEGACY_ALGORITHMS],
            "phase7e_incumbent_refit",
            *[f"phase7f_tuned_{name}" for name in tuning.TUNED_ALGORITHMS],
        )
    }
    if len(candidates) != len(expected_candidates) or set(zip(candidates.hazard, candidates.candidate_id)) != expected_candidates:
        raise ValueError("Candidate result matrix is incomplete or contains unexpected candidates")
    if len(trials) != len(expected_trials) or trial_keys != expected_trials:
        raise ValueError("XGBoost/LightGBM configuration trial log is incomplete or duplicated")
    if any(row.get("fold_count") != tuning.N_SPLITS or row.get("feature_count") != 68 for row in trials):
        raise ValueError("A tuning trial has an invalid fold count or feature count")
    if manifest.get("test_data_accessed") is not False or selection.get("test_data_accessed") is not False:
        raise ValueError("Phase 7F selection metadata claims test data was accessed")
    if manifest.get("selection_status") != "frozen_validation_only" or manifest.get("candidate_count") != len(expected_candidates):
        raise ValueError("Phase 7F experiment manifest does not describe a frozen complete selection")
    if set(thresholds.threshold.unique()) != set(tuning.THRESHOLDS) or len(thresholds) != len(tuning.HAZARD_ORDER) * len(tuning.THRESHOLDS):
        raise ValueError("Validation threshold sweep is incomplete or outside the declared grid")
    if selection.get("experiment_version") != tuning.EXPERIMENT_VERSION or selection.get("label_scope") != tuning.LABEL_SCOPE:
        raise ValueError("Selection experiment or label scope is incorrect")

    checked: list[str] = []
    test_seals = []
    for target, hazard in phase7d.HAZARDS.items():
        hazard_candidates = candidates.loc[candidates.hazard.eq(hazard)].copy()
        if hazard_candidates.selected_for_registry.astype(bool).sum() != 1:
            raise ValueError(f"Expected exactly one validation-selected candidate for {hazard}")
        ordered = max(
            hazard_candidates.to_dict(orient="records"),
            key=lambda row: (
                float(row["validation_average_precision"]),
                float(row["validation_roc_auc"]),
                -float(row["validation_false_alarm_rate_at_0_5"]),
                str(row["candidate_id"]),
            ),
        )
        model_dir = tuning.MODEL_ROOT / hazard
        model_path = model_dir / "model.joblib"
        metadata_path = model_dir / "metadata.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if not model_path.is_file() or metadata.get("model_sha256") != tuning.sha256(model_path):
            raise ValueError(f"Selected model file/hash mismatch for {hazard}")
        if metadata.get("model_version") != tuning.MODEL_VERSION or metadata.get("selected_candidate_id") != ordered["candidate_id"]:
            raise ValueError(f"Model version/selection does not match validation ranking for {hazard}")
        if metadata.get("label_scope") != tuning.LABEL_SCOPE or metadata.get("label_version") != tuning.LABEL_VERSION:
            raise ValueError(f"Synthetic scope/version missing for {hazard}")
        if metadata.get("test_data_accessed") is False:
            if metadata.get("test_metrics") is not None:
                raise ValueError(f"Test metrics exist before the test-evaluation seal for {hazard}")
            test_seals.append(False)
        elif metadata.get("test_data_accessed") is True:
            if metadata.get("test_evaluation", {}).get("status") != "completed_once" or metadata.get("test_metrics") is None:
                raise ValueError(f"Test metadata seal is incomplete for {hazard}")
            test_seals.append(True)
        else:
            raise ValueError(f"Test access metadata is absent for {hazard}")
        if metadata.get("feature_count") != 68 or len(metadata.get("feature_columns", [])) != 68:
            raise ValueError(f"Feature contract mismatch for {hazard}")
        if any("label" in feature.lower() or "event" in feature.lower() for feature in metadata["feature_columns"]):
            raise ValueError(f"A label-like predictor was found for {hazard}")

        frame, features, dataset_hash = phase7d.load_train_validation(target)
        if metadata.get("dataset_sha256") != dataset_hash or metadata.get("dataset_sha256") != phase7d.DATASET_HASHES[target]:
            raise ValueError(f"Dataset hash mismatch for {hazard}")
        if metadata.get("feature_columns") != features:
            raise ValueError(f"Feature ordering differs from the model contract for {hazard}")
        train = frame.loc[frame.split.eq("train")]
        validation = frame.loc[frame.split.eq("validation")]
        if not train.target_date.max() < validation.target_date.min():
            raise ValueError(f"Train/validation chronology failed for {hazard}")
        if int(metadata["training_period"]["rows"]) != len(train) or int(metadata["validation_period"]["rows"]) != len(validation):
            raise ValueError(f"Training/validation support mismatch for {hazard}")

        estimator = joblib.load(model_path)
        scores = tuning.positive_scores(estimator, validation[features].to_numpy(dtype=np.float32))
        labels = validation[target].to_numpy(dtype=np.int8)
        metrics = tuning.metric_bundle(labels, scores, 0.5)
        recorded = metadata["validation_metrics_at_0_5"]
        comparisons = {
            "validation_average_precision": metrics["average_precision"],
            "validation_roc_auc": metrics["roc_auc"],
            "validation_precision": metrics["precision"],
            "validation_recall": metrics["recall"],
            "validation_f1": metrics["f1"],
            "validation_false_alarm_rate": metrics["false_alarm_rate"],
            "validation_brier_score": metrics["brier_score"],
        }
        for name, value in comparisons.items():
            if not np.isclose(float(recorded[name]), float(value), rtol=1e-9, atol=1e-10):
                raise ValueError(f"Validation metric {name} does not reproduce for {hazard}")

        expected_threshold, _ = tuning.choose_threshold(labels, scores)
        chosen = metadata["threshold_selection"]
        if not np.isclose(float(chosen["selected_threshold"]), float(expected_threshold["threshold"])):
            raise ValueError(f"Validation threshold does not reproduce for {hazard}")
        if not np.isclose(float(selection["selected"][hazard]["threshold"]), float(expected_threshold["threshold"])):
            raise ValueError(f"Selection manifest threshold differs for {hazard}")
        if not np.isclose(
            float(selection["selected"][hazard]["validation_average_precision"]),
            float(ordered["validation_average_precision"]),
            rtol=1e-12,
            atol=1e-14,
        ):
            raise ValueError(f"Selection manifest metric differs for {hazard}")
        checked.append(hazard)

    if tuning.TEST_ATTEMPT_PATH.exists():
        attempt = json.loads(tuning.TEST_ATTEMPT_PATH.read_text(encoding="utf-8"))
        if attempt.get("status") != "completed_once" or not all(test_seals):
            raise ValueError("Test-evaluation attempt and model metadata seals are inconsistent")
    elif any(test_seals):
        raise ValueError("Model metadata indicates test access without an attempt marker")
    return {
        "candidate_count": len(candidates),
        "successful_trials": sum(row.get("status") == "success" for row in trials),
        "trial_count": len(trials),
        "hazards": checked,
        "test_rows_read": False,
    }


def main() -> int:
    result = validate()
    print("PHASE 7F SELECTION VALIDATION: PASS")
    print(f"Candidates: {result['candidate_count']}; boosted configurations: {result['trial_count']}")
    print(f"Successful configurations: {result['successful_trials']}")
    print(f"Selected hazard models reproduced: {len(result['hazards'])}")
    print("Frozen data hashes, validation metrics, thresholds and model hashes: PASS")
    print("Test rows opened by selection validation: No")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError, AssertionError) as exc:
        print(f"PHASE 7F SELECTION VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
