"""Verify Phase 7E model choices and thresholds without reading test rows."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

import tune_phase7e_models as tuning
from scripts.train_phase7d_baselines import HAZARDS, LABEL_SCOPE, LABEL_VERSION, load_train_validation, positive_probabilities


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate() -> list[dict[str, object]]:
    candidates = pd.read_csv(tuning.CANDIDATE_METRICS_PATH)
    thresholds = pd.read_csv(tuning.THRESHOLD_PATH)
    trial_records = [
        json.loads(line)
        for line in tuning.TRIAL_LOG.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    completed_trials = [row for row in trial_records if row.get("event") == "trial_complete"]
    expected_candidate_keys = {
        (hazard, algorithm)
        for hazard, algorithms in tuning.CANDIDATES.items()
        for algorithm in algorithms
    }
    if set(zip(candidates["hazard"], candidates["algorithm"])) != expected_candidate_keys:
        raise ValueError("Candidate metrics do not cover the configured candidates exactly")
    if len(completed_trials) < 20 * len(expected_candidate_keys):
        raise ValueError("Temporal CV trial checkpoints are incomplete")
    if not set(thresholds["threshold"].unique()) <= set(tuning.THRESHOLDS):
        raise ValueError("Threshold analysis contains a threshold outside 0.10..0.90")

    selected_metadata = []
    for target, hazard in HAZARDS.items():
        model_path = tuning.MODEL_ROOT / hazard / "model.joblib"
        metadata_path = tuning.MODEL_ROOT / hazard / "metadata.json"
        if not model_path.exists() or not metadata_path.exists():
            raise ValueError(f"Selected model or metadata missing for {hazard}")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata.get("label_scope") != LABEL_SCOPE or metadata.get("label_version") != LABEL_VERSION:
            raise ValueError(f"Synthetic development metadata missing for {hazard}")
        if metadata.get("label_type") != "synthetic_development":
            raise ValueError(f"Model label type is wrong for {hazard}")
        if metadata.get("model_version") != tuning.MODEL_VERSION:
            raise ValueError(f"Model version mismatch for {hazard}")
        if metadata.get("test_data_accessed") is False:
            if metadata.get("test_metrics") is not None:
                raise ValueError(f"Unsealed test metrics exist for {hazard}")
        elif metadata.get("test_data_accessed") is True:
            if metadata.get("test_metrics") is None or metadata.get("test_evaluation", {}).get("status") != "completed_once":
                raise ValueError(f"Final test-evaluation seal is incomplete for {hazard}")
        else:
            raise ValueError(f"Test-access metadata is missing for {hazard}")
        if metadata.get("selected_algorithm") not in tuning.CANDIDATES[hazard]:
            raise ValueError(f"Selected algorithm was not a configured candidate for {hazard}")
        if metadata.get("model_sha256") != sha256(model_path):
            raise ValueError(f"Selected model hash mismatch for {hazard}")

        frame, features, source_hash = load_train_validation(target)
        if metadata.get("dataset_sha256") != source_hash or metadata.get("dataset_sha256") != tuning.DATASET_HASHES[target]:
            raise ValueError(f"Frozen dataset hash mismatch for {hazard}")
        if metadata.get("feature_columns") != features or len(features) != 68:
            raise ValueError(f"Feature schema mismatch for {hazard}")
        if "validation_probabilities" in metadata.get("validation_metrics_at_0_5", {}):
            raise ValueError(f"Non-scalar validation probability preview is stored for {hazard}")
        if metadata.get("calibration", {}).get("calibrated") is not False:
            raise ValueError(f"Unexpected calibration state for {hazard}")

        validation = frame[frame["split"].eq("validation")]
        X_validation = validation[features].to_numpy(dtype=np.float32)
        y_validation = validation[target].to_numpy(dtype=np.int8)
        estimator = joblib.load(model_path)
        probabilities = positive_probabilities(estimator, X_validation)
        metrics_at_half = tuning.metric_bundle(y_validation, probabilities, threshold=0.5)
        recorded = metadata["validation_metrics_at_0_5"]
        if not np.isclose(
            float(recorded["validation_average_precision"]),
            float(metrics_at_half["pr_auc_average_precision"]),
            rtol=1e-10,
            atol=1e-10,
        ):
            raise ValueError(f"Selected model validation PR-AUC did not reproduce for {hazard}")

        analyzed = tuning.threshold_rows(hazard, target, y_validation, probabilities)
        expected_threshold = tuning.choose_threshold(analyzed)
        recorded_threshold = metadata["threshold_selection"]["selected_threshold"]
        if not np.isclose(float(recorded_threshold), float(expected_threshold["threshold"])):
            raise ValueError(f"Validation threshold selection did not reproduce for {hazard}")
        selected_metadata.append(metadata)

    return selected_metadata


def main() -> int:
    selected = validate()
    print("PHASE 7E SELECTION VALIDATION: PASS")
    print(f"Tuned candidates: {sum(len(value) for value in tuning.CANDIDATES.values())}")
    print(f"Selected hazards: {len(selected)}")
    print("Frozen Phase 7C dataset hashes: PASS")
    print("Synthetic model metadata: PASS")
    print("Validation metrics and thresholds reproduce: PASS")
    print("Test rows reopened by this validator: No")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, TypeError, AssertionError) as exc:
        print(f"PHASE 7E SELECTION VALIDATION FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
