"""One-time final evaluation of frozen Phase 7E synthetic models."""

from __future__ import annotations

import json
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

from scripts.train_phase7d_baselines import HAZARDS, LABEL_SCOPE, LABEL_VERSION, READ_ROWS, dataset_path
from scripts.tune_phase7e_models import MODEL_ROOT, PHASE_RESULTS, sha256

METRICS_PATH = PHASE_RESULTS / "final_test_metrics.csv"
TEST_REPORT_PATH = PROJECT_ROOT / "results" / "ml" / "phase7e_final_test_evaluation.md"
EXPECTED_DATASET_HASHES = {
    "synthetic_flood_dev_v1": "1f5a1863ecc9d5f90613fc3a5e2622711a60fd4db142662a870e0073dc53ef6e",
    "synthetic_heavy_rain_dev_v1": "ce1132ffc0c071abcfacf0892b2009ed86fc0a2e5bf13c5fa7b3d6bb5d251d05",
    "synthetic_landslide_dev_v1": "d8e1936cac26329019ceaaf943a76b0dc315764781209c1b39e2ce96890fc05e",
    "synthetic_heatwave_dev_v1": "6be7fd7c7f05ff9bc5583f17c9bb5c5143c7a8e15b3ccfc354eca43a51717537",
    "synthetic_coldwave_dev_v1": "194a57af996e577ec734246a7490f7b04a9da92229ccef95398a3472ce7282ec",
    "synthetic_windstorm_dev_v1": "4ad98dd577fa19d4a65de5e707d67ac0affce8236ca22677c084bfc0e0f56707",
}
TEST_ROWS = 20_700
MIN_SUBGROUP_CLASS_ROWS = 5
SEASON_BY_MONTH = {
    12: "winter", 1: "winter", 2: "winter",
    3: "spring", 4: "spring", 5: "spring",
    6: "summer", 7: "summer", 8: "summer",
    9: "autumn", 10: "autumn", 11: "autumn",
}


def metric_row(
    hazard: str,
    target: str,
    y_true: np.ndarray,
    probabilities: np.ndarray,
    threshold: float,
    subgroup: str,
    subgroup_value: str,
) -> dict[str, object]:
    positives = int(y_true.sum())
    negatives = int(len(y_true) - positives)
    row: dict[str, object] = {
        "hazard": hazard,
        "target": target,
        "scope": subgroup,
        "scope_value": subgroup_value,
        "rows": int(len(y_true)),
        "positive_rows": positives,
        "negative_rows": negatives,
        "threshold_from_validation": threshold,
        "evaluation_status": "evaluated",
    }
    if positives < MIN_SUBGROUP_CLASS_ROWS or negatives < MIN_SUBGROUP_CLASS_ROWS:
        row.update({
            "evaluation_status": "insufficient_subgroup_support",
            "precision": np.nan,
            "recall": np.nan,
            "f1": np.nan,
            "average_precision": np.nan,
            "roc_auc": np.nan,
            "brier_score": np.nan,
            "true_negative": np.nan,
            "false_positive": np.nan,
            "false_negative": np.nan,
            "true_positive": np.nan,
            "false_alert_rate": np.nan,
        })
        return row

    predicted = probabilities >= threshold
    tn, fp, fn, tp = (int(value) for value in confusion_matrix(y_true, predicted, labels=[0, 1]).ravel())
    row.update({
        "precision": float(precision_score(y_true, predicted, zero_division=0)),
        "recall": float(recall_score(y_true, predicted, zero_division=0)),
        "f1": float(f1_score(y_true, predicted, zero_division=0)),
        "average_precision": float(average_precision_score(y_true, probabilities)),
        "roc_auc": float(roc_auc_score(y_true, probabilities)),
        "brier_score": float(brier_score_loss(y_true, probabilities)),
        "true_negative": tn,
        "false_positive": fp,
        "false_negative": fn,
        "true_positive": tp,
        "false_alert_rate": float(fp / (fp + tn)) if fp + tn else 0.0,
    })
    return row


def load_test_only(path: Path, target: str) -> pd.DataFrame:
    frame = pd.read_csv(
        path,
        skiprows=range(1, 1 + READ_ROWS),
        nrows=TEST_ROWS,
        compression="gzip",
        parse_dates=["feature_reference_date", "target_date"],
        dtype={target: "int8"},
        low_memory=False,
    )
    if len(frame) != TEST_ROWS or set(frame["split"].unique()) != {"test"}:
        raise ValueError(f"Test-only read for {target} did not produce exactly {TEST_ROWS:,} test rows")
    if not frame["target_date"].is_monotonic_increasing:
        raise ValueError(f"Test target dates are not chronological for {target}")
    if not frame["feature_reference_date"].eq(frame["target_date"] - pd.Timedelta(days=1)).all():
        raise ValueError(f"One-day-ahead alignment failed in test rows for {target}")
    if not frame["synthetic_label_scope"].eq(LABEL_SCOPE).all() or not frame["synthetic_rule_version"].eq(LABEL_VERSION).all():
        raise ValueError(f"Synthetic metadata mismatch in test rows for {target}")
    return frame


def evaluation_is_already_sealed() -> bool:
    if METRICS_PATH.exists() or TEST_REPORT_PATH.exists():
        return True
    for target, hazard in HAZARDS.items():
        metadata_path = MODEL_ROOT / hazard / "metadata.json"
        if not metadata_path.exists():
            raise ValueError(f"Selected model metadata is missing: {metadata_path}")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata.get("test_data_accessed") is not False or metadata.get("test_metrics") is not None:
            return True
        if metadata.get("dataset_sha256") != EXPECTED_DATASET_HASHES[target]:
            raise ValueError(f"Frozen dataset hash differs for {hazard}")
        model_path = MODEL_ROOT / hazard / "model.joblib"
        if metadata.get("model_sha256") != sha256(model_path):
            raise ValueError(f"Selected model hash differs for {hazard}")
    return False


def evaluate_once() -> tuple[list[dict[str, object]], str]:
    if evaluation_is_already_sealed():
        raise FileExistsError("Final test evaluation is already sealed; refusing to read test rows again")
    PHASE_RESULTS.mkdir(parents=True, exist_ok=True)
    evaluated_at = datetime.now(timezone.utc).isoformat()
    metrics: list[dict[str, object]] = []
    model_updates: list[tuple[Path, dict[str, object]]] = []

    for target, hazard in HAZARDS.items():
        path = dataset_path(target)
        frame = load_test_only(path, target)
        model_path = MODEL_ROOT / hazard / "model.joblib"
        metadata_path = MODEL_ROOT / hazard / "metadata.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        features = metadata["feature_columns"]
        if len(features) != 68 or any("label" in name.lower() or "event" in name.lower() for name in features):
            raise ValueError(f"Invalid predictor list in frozen metadata for {hazard}")
        if set(frame["split"].unique()) != {"test"}:
            raise ValueError(f"Non-test split reached model evaluation for {hazard}")
        X_test = frame[features].to_numpy(dtype=np.float32)
        y_test = frame[target].to_numpy(dtype=np.int8)
        estimator = joblib.load(model_path)
        positive_class = np.flatnonzero(estimator.classes_ == 1)
        if len(positive_class) != 1:
            raise ValueError(f"Selected model has no unique positive class for {hazard}")
        probabilities = estimator.predict_proba(X_test)[:, int(positive_class[0])]
        threshold = float(metadata["threshold_selection"]["selected_threshold"])

        overall = metric_row(hazard, target, y_test, probabilities, threshold, "overall", "all_test_rows")
        metrics.append(overall)
        district_metrics = []
        for district, indexes in frame.groupby("district", sort=True).indices.items():
            selected = np.asarray(indexes, dtype=np.int64)
            item = metric_row(hazard, target, y_test[selected], probabilities[selected], threshold, "district", str(district))
            metrics.append(item)
            district_metrics.append(item)
        frame_seasons = frame["target_date"].dt.month.map(SEASON_BY_MONTH)
        season_metrics = []
        for season in ("winter", "spring", "summer", "autumn"):
            selected = np.flatnonzero(frame_seasons.eq(season).to_numpy())
            item = metric_row(hazard, target, y_test[selected], probabilities[selected], threshold, "season", season)
            metrics.append(item)
            season_metrics.append(item)

        metadata["test_metrics"] = {
            key: value for key, value in overall.items()
            if key not in {"scope", "scope_value", "threshold_from_validation"}
        }
        metadata["test_evaluation"] = {
            "status": "completed_once",
            "evaluated_at_utc": evaluated_at,
            "split": "test",
            "rows": TEST_ROWS,
            "start": frame["target_date"].min().strftime("%Y-%m-%d"),
            "end": frame["target_date"].max().strftime("%Y-%m-%d"),
            "threshold_source": "frozen validation-selected threshold; not retuned",
            "subgroup_rows_recorded": len(district_metrics) + len(season_metrics),
            "subgroup_support_rule": f"Metrics withheld where either class has fewer than {MIN_SUBGROUP_CLASS_ROWS} rows",
        }
        metadata["test_period"]["evaluation_status"] = "completed_once"
        metadata["test_data_accessed"] = True
        model_updates.append((metadata_path, metadata))

    columns = [
        "hazard", "target", "scope", "scope_value", "rows", "positive_rows", "negative_rows",
        "threshold_from_validation", "evaluation_status", "precision", "recall", "f1",
        "average_precision", "roc_auc", "brier_score", "true_negative", "false_positive",
        "false_negative", "true_positive", "false_alert_rate",
    ]
    metric_frame = pd.DataFrame(metrics, columns=columns)
    metric_temp = METRICS_PATH.with_name(f".{METRICS_PATH.name}.tmp")
    metric_frame.to_csv(metric_temp, index=False, encoding="utf-8")
    metric_temp.replace(METRICS_PATH)

    lines = [
        "# Phase 7E Final Test Evaluation",
        "",
        "**SYNTHETIC_DEVELOPMENT_ONLY**",
        "",
        f"One-time evaluation completed at `{evaluated_at}`. The final chronological test rows were read once; no threshold, model, or feature selection was changed from test results.",
        "",
        "These measures quantify reproduction of the synthetic Phase 7A rules only. They are not evidence of real-world hazard prediction skill, operational calibration, or verified disaster detection.",
        "",
        "## Overall Test Results",
        "",
        "| Hazard | Rows | Positives | Threshold (validation) | AP | ROC-AUC | Precision | Recall | F1 | False-alert rate | Brier |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in (item for item in metrics if item["scope"] == "overall"):
        lines.append(
            f"| {row['hazard']} | {row['rows']} | {row['positive_rows']} | {row['threshold_from_validation']:.2f} | "
            f"{row['average_precision']:.4f} | {row['roc_auc']:.4f} | {row['precision']:.4f} | "
            f"{row['recall']:.4f} | {row['f1']:.4f} | {row['false_alert_rate']:.4f} | {row['brier_score']:.4f} |"
        )
    lines.extend([
        "",
        f"District and seasonal metrics are in `results/ml/phase7e/final_test_metrics.csv`. Metrics are suppressed when a subgroup has fewer than {MIN_SUBGROUP_CLASS_ROWS} positives or negatives; subgroup sample sizes are retained.",
        "",
        "All labels remain synthetic; the reported scores must not be used for real alerts, public risk communication, or resource dispatch.",
        "",
    ])
    report_temp = TEST_REPORT_PATH.with_name(f".{TEST_REPORT_PATH.name}.tmp")
    report_temp.write_text("\n".join(lines), encoding="utf-8")
    report_temp.replace(TEST_REPORT_PATH)

    for metadata_path, metadata in model_updates:
        temporary = metadata_path.with_name(f".{metadata_path.name}.tmp")
        temporary.write_text(json.dumps(metadata, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
        temporary.replace(metadata_path)

    return metrics, evaluated_at


def main() -> int:
    metrics, _ = evaluate_once()
    overall = [row for row in metrics if row["scope"] == "overall"]
    if len(overall) != len(HAZARDS) or not METRICS_PATH.exists() or not TEST_REPORT_PATH.exists():
        raise AssertionError("Final test output completeness check failed")
    if any(row["evaluation_status"] != "evaluated" for row in overall):
        raise AssertionError("Overall hazard metrics unexpectedly lack both classes")
    for target, hazard in HAZARDS.items():
        metadata = json.loads((MODEL_ROOT / hazard / "metadata.json").read_text(encoding="utf-8"))
        if metadata.get("test_data_accessed") is not True or metadata.get("test_metrics") is None:
            raise AssertionError(f"Test-evaluation seal missing for {hazard}")
    print("PHASE 7E FINAL TEST EVALUATION: PASS")
    print(f"Hazards evaluated once: {len(overall)}")
    print(f"Aggregate/subgroup metric rows: {len(metrics)}")
    print("Thresholds: frozen from validation; no test-based tuning")
    print("Labels: SYNTHETIC_DEVELOPMENT_ONLY")
    print(f"Metrics: {METRICS_PATH.relative_to(PROJECT_ROOT)}")
    print(f"Report: {TEST_REPORT_PATH.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError, AssertionError, FileExistsError) as exc:
        print(f"PHASE 7E FINAL TEST EVALUATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
