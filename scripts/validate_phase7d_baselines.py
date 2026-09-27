"""Validate Phase 7D baseline artifacts using validation data only."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

import train_phase7d_baselines as training


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def numeric_equal(actual: object, expected: float, *, tolerance: float = 1e-10) -> bool:
    try:
        return bool(np.isclose(float(actual), expected, rtol=tolerance, atol=tolerance))
    except (TypeError, ValueError):
        return False


def validate() -> tuple[pd.DataFrame, list[str]]:
    if not training.METRICS_PATH.exists():
        raise ValueError("Phase 7D validation metrics are missing")
    metrics = pd.read_csv(training.METRICS_PATH, keep_default_na=False)
    if metrics.columns.tolist() != training.METRIC_COLUMNS:
        raise ValueError("Phase 7D metrics schema does not match the runner contract")
    if metrics.duplicated(["hazard", "algorithm"]).any():
        raise ValueError("Metrics contain duplicate hazard-algorithm rows")

    expected_keys = {
        (hazard, algorithm)
        for hazard in training.HAZARDS.values()
        for algorithm in training.ALGORITHMS
    }
    actual_keys = set(zip(metrics["hazard"], metrics["algorithm"]))
    if actual_keys != expected_keys:
        raise ValueError("Metrics do not include exactly the five baselines for all six hazards")

    successes = metrics[metrics["status"].eq("success")]
    failures = metrics[metrics["status"].eq("failed")]
    if len(successes) + len(failures) != len(metrics):
        raise ValueError("Every candidate must be marked success or failed")
    if failures["failure"].eq("").any():
        raise ValueError("A failed baseline is missing its recorded reason")

    validated = []
    for target, hazard in training.HAZARDS.items():
        frame, feature_columns, source_hash = training.load_train_validation(target)
        validation = frame[frame["split"].eq("validation")]
        X_validation = validation[feature_columns]
        y_validation = validation[target].to_numpy(dtype=np.int8)
        if not set(validation["split"].unique()) == {"validation"}:
            raise ValueError(f"{hazard} validation subset includes another split")

        hazard_rows = metrics[metrics["hazard"].eq(hazard)]
        for row in hazard_rows.to_dict(orient="records"):
            algorithm = row["algorithm"]
            model_path, metadata_path = training.artifact_paths(hazard, algorithm)
            if row["status"] == "failed":
                if model_path.exists() and not metadata_path.exists():
                    raise ValueError(f"{hazard}/{algorithm} has an incomplete failed artifact")
                continue
            if not model_path.exists() or not metadata_path.exists():
                raise ValueError(f"{hazard}/{algorithm} is missing a saved model or metadata")

            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            if metadata.get("status") != "success":
                raise ValueError(f"{hazard}/{algorithm} metadata is not marked successful")
            if metadata.get("label_scope") != training.LABEL_SCOPE:
                raise ValueError(f"{hazard}/{algorithm} is missing synthetic-only scope")
            if metadata.get("label_version") != training.LABEL_VERSION:
                raise ValueError(f"{hazard}/{algorithm} has the wrong label version")
            if metadata.get("dataset_sha256") != source_hash or source_hash != training.DATASET_HASHES[target]:
                raise ValueError(f"{hazard}/{algorithm} source dataset hash mismatch")
            if metadata.get("feature_columns") != feature_columns or len(feature_columns) != 68:
                raise ValueError(f"{hazard}/{algorithm} predictor schema mismatch")
            if metadata.get("feature_count") != 68:
                raise ValueError(f"{hazard}/{algorithm} has the wrong feature count")
            if metadata.get("test_data_accessed") is not False or metadata.get("test_metrics") is not None:
                raise ValueError(f"{hazard}/{algorithm} records test-set access or metrics")
            if metadata.get("model_size_bytes") != model_path.stat().st_size:
                raise ValueError(f"{hazard}/{algorithm} model size metadata mismatch")
            if metadata.get("model_sha256") != sha256(model_path):
                raise ValueError(f"{hazard}/{algorithm} model hash mismatch")
            if row["model_path"] != model_path.relative_to(PROJECT_ROOT).as_posix():
                raise ValueError(f"{hazard}/{algorithm} metrics reference the wrong model path")

            estimator = joblib.load(model_path)
            probabilities = training.positive_probabilities(estimator, X_validation)
            if len(probabilities) != len(validation) or not np.isfinite(probabilities).all():
                raise ValueError(f"{hazard}/{algorithm} produced invalid validation probabilities")
            if (probabilities < 0).any() or (probabilities > 1).any():
                raise ValueError(f"{hazard}/{algorithm} probabilities fall outside [0, 1]")
            measured = training.calculate_metrics(y_validation, probabilities)
            for metric_name, expected in measured.items():
                if not numeric_equal(row[metric_name], float(expected)):
                    raise ValueError(f"{hazard}/{algorithm} stored {metric_name} does not reproduce")
                if not numeric_equal(metadata["validation_metrics"][metric_name], float(expected)):
                    raise ValueError(f"{hazard}/{algorithm} metadata {metric_name} does not reproduce")
            validated.append(row)
        del frame

    if not validated:
        raise ValueError("No successful baseline models were available to validate")
    return metrics, validated


def report_text(metrics: pd.DataFrame, validated: list[dict[str, object]]) -> str:
    lines = [
        "# Phase 7D Baseline Training and Validation",
        "",
        "**SYNTHETIC_DEVELOPMENT_ONLY**",
        "",
        "## Result",
        "",
        "All completed baseline artifacts and validation metrics were checked. Results measure how well models reproduce the Phase 7A synthetic weather-rule targets; they are not evidence of real disaster prediction skill.",
        "",
        f"- Baseline candidates: {len(metrics)} across six hazards and five algorithms.",
        f"- Successful: {len(validated)}; recorded failures: {int(metrics['status'].eq('failed').sum())}.",
        "- Train data: Phase 5 `train` split only; validation data: Phase 5 `validation` split only.",
        "- Test data: not read, evaluated, or used for selection. Test metrics are intentionally absent.",
        "- `UNAVAILABLE` labels were already excluded in Phase 7C and were not recoded.",
        "- Class imbalance: balanced class weights were used for Logistic Regression, Decision Tree, Random Forest, and Extra Trees; balanced per-row weights were used for HistGradientBoosting.",
        "- Probability threshold: 0.50 for threshold metrics; PR-AUC is average precision and does not depend on that threshold.",
        "- Model selection: no final champion or operating threshold is selected in this baseline phase.",
        "- XGBoost and LightGBM: not run because neither was present in the available environment.",
        "- No hyperparameter search or tuning was performed.",
        "",
        "## Validation metrics",
        "",
        "| Hazard | Algorithm | Train positives | Validation positives | Precision | Recall | F1 | PR-AUC | ROC-AUC | False-alert rate | Brier | Train seconds | Model bytes |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in sorted(validated, key=lambda item: (item["hazard"], item["algorithm"])):
        lines.append(
            f"| {row['hazard']} | {row['algorithm']} | {int(row['train_positives']):,} | "
            f"{int(row['validation_positives']):,} | {float(row['precision']):.4f} | "
            f"{float(row['recall']):.4f} | {float(row['f1']):.4f} | "
            f"{float(row['pr_auc_average_precision']):.4f} | {float(row['roc_auc']):.4f} | "
            f"{float(row['false_alert_rate']):.4f} | {float(row['brier_score']):.4f} | "
            f"{float(row['training_seconds']):.1f} | {int(row['model_size_bytes']):,} |"
        )
    if not metrics[metrics["status"].eq("failed")].empty:
        lines.extend(["", "## Recorded failures", ""])
        for row in metrics[metrics["status"].eq("failed")].to_dict(orient="records"):
            lines.append(f"- {row['hazard']} / {row['algorithm']}: {row['failure']}")
    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            "- Metrics: `results/ml/phase7d_baseline_validation_metrics.csv`.",
            "- Experiment log: `results/ml/phase7d_baseline_experiment_log.jsonl`.",
            "- Models and per-model metadata: `models/development/phase7d/`.",
            "- Validation script: `scripts/validate_phase7d_baselines.py`.",
            "- Algorithms: Logistic Regression, Decision Tree, Random Forest, Extra Trees, HistGradientBoosting.",
            "- Metrics include precision, recall, F1, average precision (PR-AUC), ROC-AUC, Brier score, confusion counts, false-alert rate, fit time, and serialized model size.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    metrics, validated = validate()
    training.REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    training.REPORT_PATH.write_text(report_text(metrics, validated), encoding="utf-8")
    print("PHASE 7D VALIDATION: PASS")
    print(f"Successful models independently reproduced: {len(validated)}")
    print(f"Recorded baseline failures: {int(metrics['status'].eq('failed').sum())}")
    print("Test split read: No")
    print("Synthetic-only metadata: PASS")
    print(f"Report: {training.REPORT_PATH}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, TypeError, AssertionError) as exc:
        print(f"PHASE 7D VALIDATION FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
