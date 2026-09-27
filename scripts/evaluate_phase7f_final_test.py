"""One-time final test evaluation for frozen Phase 7F synthetic models."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import tune_phase7f_models as tuning
import train_phase7d_baselines as phase7d
from validate_phase7f_selection import validate as validate_selection

PHASE_RESULTS = tuning.OUTPUT_DIR
METRICS_PATH = PHASE_RESULTS / "final_test_metrics.csv"
REPORT_PATH = PROJECT_ROOT / "results" / "ml" / "phase7f_final_test_evaluation.md"
TEST_ATTEMPT_PATH = PHASE_RESULTS / "final_test_evaluation_attempt.json"
TEST_ROWS = 20_700
MIN_SUBGROUP_CLASS_ROWS = 5
SEASON_BY_MONTH = {
    12: "winter", 1: "winter", 2: "winter",
    3: "spring", 4: "spring", 5: "spring",
    6: "summer", 7: "summer", 8: "summer",
    9: "autumn", 10: "autumn", 11: "autumn",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def metric_row(
    hazard: str,
    target: str,
    labels: np.ndarray,
    raw_scores: np.ndarray,
    threshold: float,
    scope: str,
    scope_value: str,
) -> dict[str, object]:
    positives = int(labels.sum())
    negatives = int(len(labels) - positives)
    row: dict[str, object] = {
        "hazard": hazard,
        "target": target,
        "scope": scope,
        "scope_value": scope_value,
        "rows": int(len(labels)),
        "positive_rows": positives,
        "negative_rows": negatives,
        "threshold_from_validation": threshold,
        "evaluation_status": "evaluated",
    }
    if scope != "overall" and min(positives, negatives) < MIN_SUBGROUP_CLASS_ROWS:
        row.update({
            "evaluation_status": "insufficient_subgroup_support",
            "precision": np.nan,
            "recall": np.nan,
            "f1": np.nan,
            "average_precision": np.nan,
            "roc_auc": np.nan,
            "brier_score_raw_score_diagnostic": np.nan,
            "true_negative": np.nan,
            "false_positive": np.nan,
            "false_negative": np.nan,
            "true_positive": np.nan,
            "false_alarm_rate": np.nan,
        })
        return row
    if positives == 0 or negatives == 0:
        raise ValueError(f"Overall test rows do not contain both classes for {hazard}")

    predicted = raw_scores >= threshold
    tn, fp, fn, tp = (int(value) for value in confusion_matrix(labels, predicted, labels=[0, 1]).ravel())
    row.update({
        "precision": float(precision_score(labels, predicted, zero_division=0)),
        "recall": float(recall_score(labels, predicted, zero_division=0)),
        "f1": float(f1_score(labels, predicted, zero_division=0)),
        "average_precision": float(average_precision_score(labels, raw_scores)),
        "roc_auc": float(roc_auc_score(labels, raw_scores)),
        "brier_score_raw_score_diagnostic": float(brier_score_loss(labels, raw_scores)),
        "true_negative": tn,
        "false_positive": fp,
        "false_negative": fn,
        "true_positive": tp,
        "false_alarm_rate": float(fp / (fp + tn)) if fp + tn else 0.0,
    })
    return row


def load_test_only(path: Path, target: str) -> pd.DataFrame:
    if sha256(path) != phase7d.DATASET_HASHES[target]:
        raise ValueError(f"Frozen Phase 7C dataset hash mismatch for {target}")
    frame = pd.read_csv(
        path,
        skiprows=range(1, 1 + phase7d.READ_ROWS),
        nrows=TEST_ROWS,
        compression="gzip",
        parse_dates=["feature_reference_date", "target_date"],
        dtype={target: "int8"},
        low_memory=False,
    )
    if len(frame) != TEST_ROWS or set(frame.split.unique()) != {"test"}:
        raise ValueError(f"Test-only read for {target} did not return exactly {TEST_ROWS:,} test rows")
    if not frame.target_date.is_monotonic_increasing:
        raise ValueError(f"Test dates are not chronological for {target}")
    if not frame.feature_reference_date.eq(frame.target_date - pd.Timedelta(days=1)).all():
        raise ValueError(f"Feature/target date alignment failed for {target}")
    if not frame.synthetic_label_scope.eq(tuning.LABEL_SCOPE).all() or not frame.synthetic_rule_version.eq(tuning.LABEL_VERSION).all():
        raise ValueError(f"Synthetic development metadata mismatch for {target}")
    return frame


def validate_frozen_selection() -> dict[str, dict[str, object]]:
    if not tuning.SELECTION_PATH.is_file() or not tuning.CANDIDATE_METRICS_PATH.is_file() or not tuning.SELECTION_REPORT_PATH.is_file():
        raise ValueError("Validation-only selection artifacts are incomplete")
    selection = json.loads(tuning.SELECTION_PATH.read_text(encoding="utf-8"))
    if selection.get("test_data_accessed") is not False or selection.get("selection_metric") != "validation_average_precision":
        raise ValueError("Selection is not frozen on validation-only evidence")
    frozen = {}
    for target, hazard in phase7d.HAZARDS.items():
        metadata_path = tuning.MODEL_ROOT / hazard / "metadata.json"
        model_path = tuning.MODEL_ROOT / hazard / "model.joblib"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata.get("test_data_accessed") is not False or metadata.get("test_metrics") is not None:
            raise ValueError(f"Test data is already sealed/accessed for Phase 7F hazard {hazard}")
        if metadata.get("selected_algorithm") != selection["selected"][hazard]["algorithm"]:
            raise ValueError(f"Selected algorithm changed for {hazard}")
        if metadata.get("selected_candidate_id") != selection["selected"][hazard]["candidate_id"]:
            raise ValueError(f"Selected candidate changed for {hazard}")
        if metadata.get("model_sha256") != sha256(model_path):
            raise ValueError(f"Selected model hash mismatch for {hazard}")
        if metadata.get("dataset_sha256") != phase7d.DATASET_HASHES[target]:
            raise ValueError(f"Dataset hash mismatch for {hazard}")
        if float(metadata["threshold_selection"]["selected_threshold"]) != float(selection["selected"][hazard]["threshold"]):
            raise ValueError(f"Selected threshold changed for {hazard}")
        frozen[hazard] = {"target": target, "metadata_path": metadata_path, "model_path": model_path, "metadata": metadata}
    return frozen


def seal_test_attempt() -> None:
    PHASE_RESULTS.mkdir(parents=True, exist_ok=True)
    record = {
        "experiment_version": tuning.EXPERIMENT_VERSION,
        "status": "test_read_started; rerun prohibited even after interruption",
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "test_data_accessed": True,
        "selection_metric": "validation_average_precision",
        "thresholds_frozen_from": "validation",
    }
    with TEST_ATTEMPT_PATH.open("x", encoding="utf-8") as marker:
        marker.write(json.dumps(record, indent=2, sort_keys=True) + "\n")
        marker.flush()
        os.fsync(marker.fileno())


def evaluate_once() -> tuple[list[dict[str, object]], str]:
    if TEST_ATTEMPT_PATH.exists() or METRICS_PATH.exists() or REPORT_PATH.exists():
        raise FileExistsError("Phase 7F final test attempt/output exists; refusing to read test rows again")
    validate_selection()
    frozen = validate_frozen_selection()
    seal_test_attempt()
    evaluated_at = datetime.now(timezone.utc).isoformat()
    metrics: list[dict[str, object]] = []
    metadata_updates: list[tuple[Path, dict[str, object]]] = []

    for target, hazard in phase7d.HAZARDS.items():
        item = frozen[hazard]
        metadata = item["metadata"]
        frame = load_test_only(phase7d.dataset_path(target), target)
        features = metadata["feature_columns"]
        if len(features) != 68 or any("label" in feature.lower() or "event" in feature.lower() for feature in features):
            raise ValueError(f"Predictor contract failed for {hazard}")
        X_test = frame[features].to_numpy(dtype=np.float32)
        y_test = frame[target].to_numpy(dtype=np.int8)
        estimator = joblib.load(item["model_path"])
        positive_class = np.flatnonzero(np.asarray(estimator.classes_) == 1)
        if len(positive_class) != 1:
            raise ValueError(f"Selected model does not expose exactly one positive class for {hazard}")
        raw_scores = np.asarray(estimator.predict_proba(X_test)[:, int(positive_class[0])], dtype=float)
        if not np.isfinite(raw_scores).all() or (raw_scores < 0).any() or (raw_scores > 1).any():
            raise ValueError(f"Invalid raw model scores for {hazard}")
        threshold = float(metadata["threshold_selection"]["selected_threshold"])

        overall = metric_row(hazard, target, y_test, raw_scores, threshold, "overall", "all_test_rows")
        metrics.append(overall)
        district_metrics = []
        for district, indexes in frame.groupby("district", sort=True).indices.items():
            selected = np.asarray(indexes, dtype=np.int64)
            row = metric_row(hazard, target, y_test[selected], raw_scores[selected], threshold, "district", str(district))
            metrics.append(row)
            district_metrics.append(row)
        seasons = frame.target_date.dt.month.map(SEASON_BY_MONTH)
        seasonal_metrics = []
        for season in ("winter", "spring", "summer", "autumn"):
            selected = np.flatnonzero(seasons.eq(season).to_numpy())
            row = metric_row(hazard, target, y_test[selected], raw_scores[selected], threshold, "season", season)
            metrics.append(row)
            seasonal_metrics.append(row)

        metadata["test_metrics"] = {
            key: value for key, value in overall.items()
            if key not in {"scope", "scope_value", "threshold_from_validation"}
        }
        metadata["test_evaluation"] = {
            "status": "completed_once",
            "evaluated_at_utc": evaluated_at,
            "split": "test",
            "rows": TEST_ROWS,
            "start": frame.target_date.min().strftime("%Y-%m-%d"),
            "end": frame.target_date.max().strftime("%Y-%m-%d"),
            "threshold_source": "frozen validation-selected threshold; not retuned",
            "subgroup_rows_recorded": len(district_metrics) + len(seasonal_metrics),
            "subgroup_support_rule": f"Metrics withheld if either class has fewer than {MIN_SUBGROUP_CLASS_ROWS} examples",
            "same_interval_previously_evaluated_by": "phase7e_v1; Phase 7F test metrics were not used for Phase 7F selection",
            "score_semantics": "raw uncalibrated estimator score; Brier score is a raw-score diagnostic, not a calibration claim",
        }
        metadata["test_period"]["evaluation_status"] = "completed_once"
        metadata["test_data_accessed"] = True
        metadata_updates.append((item["metadata_path"], metadata))
        del frame, X_test, y_test, raw_scores, estimator

    columns = [
        "hazard", "target", "scope", "scope_value", "rows", "positive_rows", "negative_rows",
        "threshold_from_validation", "evaluation_status", "precision", "recall", "f1",
        "average_precision", "roc_auc", "brier_score_raw_score_diagnostic", "true_negative",
        "false_positive", "false_negative", "true_positive", "false_alarm_rate",
    ]
    metric_frame = pd.DataFrame(metrics, columns=columns)
    metrics_temp = METRICS_PATH.with_name(f".{METRICS_PATH.name}.tmp")
    metric_frame.to_csv(metrics_temp, index=False, encoding="utf-8")
    metrics_temp.replace(METRICS_PATH)

    lines = [
        "# Phase 7F v1 Final Test Evaluation",
        "",
        "**SYNTHETIC_DEVELOPMENT_ONLY**",
        "",
        f"One-time evaluation completed at `{evaluated_at}`. The 20,700-row chronological test split per hazard was read after model and threshold selection were frozen.",
        "",
        "Scores assess reproduction of synthetic Phase 7A rules only. They are not real-world disaster forecasting accuracy, calibrated probabilities, or evidence for operational warning or dispatch.",
        "",
        "The same chronological interval was already evaluated once by Phase 7E. These Phase 7F results were not used for tuning or selection, but this interval is not an independent project-wide pristine holdout.",
        "",
        "## Overall Results",
        "",
        "| Hazard | Rows | Positive | Negative | Validation threshold | AP | ROC-AUC | Precision | Recall | F1 | FAR | Raw-score Brier diagnostic |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in (item for item in metrics if item["scope"] == "overall"):
        lines.append(
            f"| {row['hazard']} | {row['rows']} | {row['positive_rows']} | {row['negative_rows']} | "
            f"{row['threshold_from_validation']:.2f} | {row['average_precision']:.4f} | {row['roc_auc']:.4f} | "
            f"{row['precision']:.4f} | {row['recall']:.4f} | {row['f1']:.4f} | "
            f"{row['false_alarm_rate']:.4f} | {row['brier_score_raw_score_diagnostic']:.4f} |"
        )
    lines.extend([
        "",
        f"District/season records are in `results/ml/phase7f/final_test_metrics.csv`. Subgroup metrics are withheld below {MIN_SUBGROUP_CLASS_ROWS} positives or negatives; subgroup support counts remain visible.",
        "",
        "Selected models, feature contracts, thresholds, and model hashes are unchanged. The registry metadata records this evaluation as completed once.",
        "",
    ])
    report_temp = REPORT_PATH.with_name(f".{REPORT_PATH.name}.tmp")
    report_temp.write_text("\n".join(lines), encoding="utf-8")
    report_temp.replace(REPORT_PATH)

    for metadata_path, metadata in metadata_updates:
        temporary = metadata_path.with_name(f".{metadata_path.name}.tmp")
        temporary.write_text(json.dumps(metadata, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
        temporary.replace(metadata_path)

    attempt = json.loads(TEST_ATTEMPT_PATH.read_text(encoding="utf-8"))
    attempt.update({
        "status": "completed_once",
        "completed_at_utc": evaluated_at,
        "hazards_evaluated": len(phase7d.HAZARDS),
        "rows_per_hazard": TEST_ROWS,
        "metrics_artifact": METRICS_PATH.relative_to(PROJECT_ROOT).as_posix(),
    })
    attempt_temp = TEST_ATTEMPT_PATH.with_name(f".{TEST_ATTEMPT_PATH.name}.tmp")
    attempt_temp.write_text(json.dumps(attempt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    attempt_temp.replace(TEST_ATTEMPT_PATH)

    return metrics, evaluated_at


def main() -> int:
    metrics, _ = evaluate_once()
    overall = [row for row in metrics if row["scope"] == "overall"]
    if len(overall) != len(phase7d.HAZARDS) or len(metrics) != len(phase7d.HAZARDS) * 25:
        raise AssertionError("Overall/subgroup final test outputs are incomplete")
    if any(row["evaluation_status"] != "evaluated" for row in overall):
        raise AssertionError("Overall evaluation unexpectedly lacks class support")
    print("PHASE 7F FINAL TEST EVALUATION: PASS")
    print(f"Hazards: {len(overall)}; overall rows: {len(overall)}; subgroup rows: {len(metrics) - len(overall)}")
    print(f"Test rows per hazard: {TEST_ROWS:,}; total hazard-row evaluations: {TEST_ROWS * len(overall):,}")
    print("Thresholds: frozen from validation; selection unchanged")
    print("Labels: SYNTHETIC_DEVELOPMENT_ONLY; raw uncalibrated estimator scores")
    print(f"Metrics: {METRICS_PATH.relative_to(PROJECT_ROOT)}")
    print(f"Report: {REPORT_PATH.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError, AssertionError, FileExistsError) as exc:
        print(f"PHASE 7F FINAL TEST EVALUATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
