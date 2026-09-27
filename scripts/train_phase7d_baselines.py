"""Train Phase 7D synthetic-development baselines on train/validation only."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import traceback
import warnings
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import scipy
import sklearn
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier
from sklearn.utils.class_weight import compute_sample_weight


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "development" / "model_ready"
MODEL_ROOT = PROJECT_ROOT / "models" / "development" / "phase7d"
RESULTS_DIR = PROJECT_ROOT / "results" / "ml"
METRICS_PATH = RESULTS_DIR / "phase7d_baseline_validation_metrics.csv"
LOG_PATH = RESULTS_DIR / "phase7d_baseline_experiment_log.jsonl"
REPORT_PATH = RESULTS_DIR / "phase7d_baseline_report.md"

RANDOM_SEED = 42
LABEL_SCOPE = "SYNTHETIC_DEVELOPMENT_ONLY"
LABEL_VERSION = "phase7a_v1"
DATASET_VERSION = "phase7c_v1"
FEATURE_SCHEMA_VERSION = "phase5_68_shifted_weather_v1"
TRAIN_ROWS = 14_480
VALIDATION_ROWS = 7_300
READ_ROWS = TRAIN_ROWS + VALIDATION_ROWS
VALIDATION_THRESHOLD = 0.5
MAX_WORKERS = max(1, min(4, os.cpu_count() or 1))

HAZARDS = {
    "synthetic_flood_dev_v1": "flood",
    "synthetic_heavy_rain_dev_v1": "heavy_rain",
    "synthetic_landslide_dev_v1": "landslide",
    "synthetic_heatwave_dev_v1": "heatwave",
    "synthetic_coldwave_dev_v1": "coldwave",
    "synthetic_windstorm_dev_v1": "windstorm",
}

DATASET_HASHES = {
    "synthetic_flood_dev_v1": "1f5a1863ecc9d5f90613fc3a5e2622711a60fd4db142662a870e0073dc53ef6e",
    "synthetic_heavy_rain_dev_v1": "ce1132ffc0c071abcfacf0892b2009ed86fc0a2e5bf13c5fa7b3d6bb5d251d05",
    "synthetic_landslide_dev_v1": "d8e1936cac26329019ceaaf943a76b0dc315764781209c1b39e2ce96890fc05e",
    "synthetic_heatwave_dev_v1": "6be7fd7c7f05ff9bc5583f17c9bb5c5143c7a8e15b3ccfc354eca43a51717537",
    "synthetic_coldwave_dev_v1": "194a57af996e577ec734246a7490f7b04a9da92229ccef95398a3472ce7282ec",
    "synthetic_windstorm_dev_v1": "4ad98dd577fa19d4a65de5e707d67ac0affce8236ca22677c084bfc0e0f56707",
}

METRIC_COLUMNS = [
    "hazard",
    "target",
    "algorithm",
    "status",
    "failure",
    "experiment_id",
    "dataset_version",
    "label_version",
    "label_scope",
    "dataset_path",
    "dataset_sha256",
    "feature_schema_version",
    "feature_count",
    "train_rows",
    "train_positives",
    "train_negatives",
    "train_start",
    "train_end",
    "validation_rows",
    "validation_positives",
    "validation_negatives",
    "validation_start",
    "validation_end",
    "threshold",
    "precision",
    "recall",
    "f1",
    "pr_auc_average_precision",
    "roc_auc",
    "brier_score",
    "true_negative",
    "false_positive",
    "false_negative",
    "true_positive",
    "false_alert_rate",
    "training_seconds",
    "model_size_bytes",
    "random_seed",
    "hyperparameters_json",
    "python_version",
    "pandas_version",
    "numpy_version",
    "scipy_version",
    "scikit_learn_version",
    "joblib_version",
    "model_path",
    "metadata_path",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def dataset_path(target: str) -> Path:
    return DATA_DIR / f"phase7c_{target}.csv.gz"


def model_key(hazard: str, algorithm: str) -> str:
    return f"{hazard}|{algorithm}"


def artifact_paths(hazard: str, algorithm: str) -> tuple[Path, Path]:
    directory = MODEL_ROOT / hazard
    return directory / f"{algorithm}.joblib", directory / f"{algorithm}.json"


def append_event(event: dict[str, object]) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as log:
        log.write(json.dumps(event, sort_keys=True, default=str) + "\n")
        log.flush()
        os.fsync(log.fileno())


def write_metrics(rows: dict[str, dict[str, object]]) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(list(rows.values()), columns=METRIC_COLUMNS)
    frame = frame.sort_values(["hazard", "algorithm"], kind="stable")
    temporary = METRICS_PATH.with_name(f".{METRICS_PATH.name}.tmp")
    frame.to_csv(temporary, index=False, encoding="utf-8")
    temporary.replace(METRICS_PATH)


def load_existing_metrics() -> dict[str, dict[str, object]]:
    if not METRICS_PATH.exists():
        return {}
    frame = pd.read_csv(METRICS_PATH, dtype=str, keep_default_na=False)
    if frame.columns.tolist() != METRIC_COLUMNS:
        raise ValueError(f"Existing metrics schema is incompatible: {METRICS_PATH}")
    rows: dict[str, dict[str, object]] = {}
    for row in frame.to_dict(orient="records"):
        rows[model_key(row["hazard"], row["algorithm"])] = row
    return rows


def load_train_validation(target: str) -> tuple[pd.DataFrame, list[str], str]:
    path = dataset_path(target)
    if not path.exists():
        raise ValueError(f"Required Phase 7C dataset is missing: {path.relative_to(PROJECT_ROOT)}")
    source_hash = sha256(path)
    if source_hash != DATASET_HASHES[target]:
        raise ValueError(f"Phase 7C dataset hash changed: {path.relative_to(PROJECT_ROOT)}")

    frame = pd.read_csv(
        path,
        nrows=READ_ROWS,
        compression="gzip",
        parse_dates=["feature_reference_date", "target_date"],
        dtype={target: "int8"},
        low_memory=False,
    )
    if len(frame) != READ_ROWS:
        raise ValueError(f"{target} exposes {len(frame):,} rows before test; expected {READ_ROWS:,}")
    if set(frame["split"].unique()) != {"train", "validation"}:
        raise ValueError(f"{target} train/validation prefix contains an unexpected split")
    if frame["split"].value_counts().to_dict() != {"train": TRAIN_ROWS, "validation": VALIDATION_ROWS}:
        raise ValueError(f"{target} train/validation row counts differ from Phase 7C")
    if frame["target_date"].is_monotonic_increasing is False:
        raise ValueError(f"{target} is not chronological")
    if not frame["feature_reference_date"].eq(frame["target_date"] - pd.Timedelta(days=1)).all():
        raise ValueError(f"{target} violates one-day-ahead target alignment")
    if not frame["synthetic_label_scope"].eq(LABEL_SCOPE).all():
        raise ValueError(f"{target} has incorrect synthetic scope")
    if not frame["synthetic_rule_version"].eq(LABEL_VERSION).all():
        raise ValueError(f"{target} has incorrect synthetic label version")

    metadata = {
        "district",
        "feature_reference_date",
        "target_date",
        "split",
        "synthetic_label_scope",
        "synthetic_rule_version",
    }
    feature_columns = [column for column in frame.columns if column not in metadata | {target}]
    if len(feature_columns) != 68:
        raise ValueError(f"{target} has {len(feature_columns)} predictors; expected 68")
    if any("label" in column.lower() or "event" in column.lower() for column in feature_columns):
        raise ValueError(f"{target} feature list contains a label/event-like column")
    if frame[feature_columns].isna().any().any():
        raise ValueError(f"{target} train/validation features contain missing values")
    return frame, feature_columns, source_hash


def build_estimator(algorithm: str):
    if algorithm == "logistic_regression":
        return make_pipeline(
            StandardScaler(),
            LogisticRegression(
                C=1.0,
                class_weight="balanced",
                max_iter=2000,
                random_state=RANDOM_SEED,
                solver="lbfgs",
            ),
        )
    if algorithm == "decision_tree":
        return DecisionTreeClassifier(
            class_weight="balanced",
            max_depth=8,
            min_samples_leaf=20,
            random_state=RANDOM_SEED,
        )
    if algorithm == "random_forest":
        return RandomForestClassifier(
            class_weight="balanced_subsample",
            max_depth=16,
            max_features="sqrt",
            min_samples_leaf=10,
            n_estimators=200,
            n_jobs=MAX_WORKERS,
            random_state=RANDOM_SEED,
        )
    if algorithm == "extra_trees":
        return ExtraTreesClassifier(
            class_weight="balanced",
            max_depth=16,
            max_features="sqrt",
            min_samples_leaf=10,
            n_estimators=200,
            n_jobs=MAX_WORKERS,
            random_state=RANDOM_SEED,
        )
    if algorithm == "hist_gradient_boosting":
        return HistGradientBoostingClassifier(
            early_stopping=False,
            l2_regularization=1.0,
            learning_rate=0.08,
            max_iter=150,
            max_leaf_nodes=15,
            min_samples_leaf=30,
            random_state=RANDOM_SEED,
        )
    raise ValueError(f"Unknown baseline algorithm: {algorithm}")


ALGORITHMS = [
    "logistic_regression",
    "decision_tree",
    "random_forest",
    "extra_trees",
    "hist_gradient_boosting",
]


def hyperparameters(algorithm: str) -> tuple[dict[str, object], str]:
    definitions = {
        "logistic_regression": (
            {
                "C": 1.0,
                "class_weight": "balanced",
                "max_iter": 2000,
                "solver": "lbfgs",
                "scaler": "StandardScaler",
            },
            "balanced class_weight; standardized predictors",
        ),
        "decision_tree": (
            {"max_depth": 8, "min_samples_leaf": 20, "class_weight": "balanced"},
            "balanced class_weight",
        ),
        "random_forest": (
            {
                "n_estimators": 200,
                "max_depth": 16,
                "min_samples_leaf": 10,
                "max_features": "sqrt",
                "class_weight": "balanced_subsample",
                "n_jobs": MAX_WORKERS,
            },
            "balanced_subsample class weights",
        ),
        "extra_trees": (
            {
                "n_estimators": 200,
                "max_depth": 16,
                "min_samples_leaf": 10,
                "max_features": "sqrt",
                "class_weight": "balanced",
                "n_jobs": MAX_WORKERS,
            },
            "balanced class_weight",
        ),
        "hist_gradient_boosting": (
            {
                "max_iter": 150,
                "max_leaf_nodes": 15,
                "min_samples_leaf": 30,
                "learning_rate": 0.08,
                "l2_regularization": 1.0,
                "early_stopping": False,
            },
            "balanced per-row sample_weight; early stopping disabled to preserve time order",
        ),
    }
    params, imbalance = definitions[algorithm]
    return {**params, "random_state": RANDOM_SEED}, imbalance


def positive_probabilities(estimator, features: pd.DataFrame) -> np.ndarray:
    classes = estimator.classes_
    indexes = np.flatnonzero(classes == 1)
    if len(indexes) != 1:
        raise ValueError("Fitted estimator has no unique positive class")
    return estimator.predict_proba(features)[:, int(indexes[0])]


def calculate_metrics(y_true: np.ndarray, probabilities: np.ndarray) -> dict[str, float | int]:
    predicted = probabilities >= VALIDATION_THRESHOLD
    tn, fp, fn, tp = (int(item) for item in confusion_matrix(y_true, predicted, labels=[0, 1]).ravel())
    return {
        "threshold": VALIDATION_THRESHOLD,
        "precision": float(precision_score(y_true, predicted, zero_division=0)),
        "recall": float(recall_score(y_true, predicted, zero_division=0)),
        "f1": float(f1_score(y_true, predicted, zero_division=0)),
        "pr_auc_average_precision": float(average_precision_score(y_true, probabilities)),
        "roc_auc": float(roc_auc_score(y_true, probabilities)),
        "brier_score": float(brier_score_loss(y_true, probabilities)),
        "true_negative": tn,
        "false_positive": fp,
        "false_negative": fn,
        "true_positive": tp,
        "false_alert_rate": float(fp / (fp + tn)) if fp + tn else 0.0,
    }


def feature_importance(estimator, feature_columns: list[str]) -> list[dict[str, object]]:
    fitted = estimator
    if hasattr(estimator, "named_steps"):
        fitted = estimator.named_steps["logisticregression"]
    if hasattr(fitted, "feature_importances_"):
        values = np.asarray(fitted.feature_importances_).ravel()
        method = "tree impurity importance"
    elif hasattr(fitted, "coef_"):
        values = np.abs(np.asarray(fitted.coef_)[0])
        method = "absolute standardized logistic coefficient"
    else:
        return []
    order = np.argsort(values)[::-1][:15]
    return [
        {"feature": feature_columns[int(index)], "importance": float(values[index]), "method": method}
        for index in order
    ]


def atomic_json(path: Path, data: dict[str, object]) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(data, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    temporary.replace(path)


def make_base_row(
    hazard: str,
    target: str,
    algorithm: str,
    source_hash: str,
    frame: pd.DataFrame,
    feature_columns: list[str],
    model_path: Path,
    metadata_path: Path,
) -> dict[str, object]:
    train = frame[frame["split"].eq("train")]
    validation = frame[frame["split"].eq("validation")]
    train_y = train[target].to_numpy(dtype=np.int8)
    validation_y = validation[target].to_numpy(dtype=np.int8)
    params, _ = hyperparameters(algorithm)
    return {
        "hazard": hazard,
        "target": target,
        "algorithm": algorithm,
        "status": "pending",
        "failure": "",
        "experiment_id": f"phase7d_v1_{hazard}_{algorithm}",
        "dataset_version": DATASET_VERSION,
        "label_version": LABEL_VERSION,
        "label_scope": LABEL_SCOPE,
        "dataset_path": dataset_path(target).relative_to(PROJECT_ROOT).as_posix(),
        "dataset_sha256": source_hash,
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "feature_count": len(feature_columns),
        "train_rows": len(train),
        "train_positives": int(train_y.sum()),
        "train_negatives": int(len(train_y) - train_y.sum()),
        "train_start": train["target_date"].min().strftime("%Y-%m-%d"),
        "train_end": train["target_date"].max().strftime("%Y-%m-%d"),
        "validation_rows": len(validation),
        "validation_positives": int(validation_y.sum()),
        "validation_negatives": int(len(validation_y) - validation_y.sum()),
        "validation_start": validation["target_date"].min().strftime("%Y-%m-%d"),
        "validation_end": validation["target_date"].max().strftime("%Y-%m-%d"),
        "threshold": VALIDATION_THRESHOLD,
        "precision": "",
        "recall": "",
        "f1": "",
        "pr_auc_average_precision": "",
        "roc_auc": "",
        "brier_score": "",
        "true_negative": "",
        "false_positive": "",
        "false_negative": "",
        "true_positive": "",
        "false_alert_rate": "",
        "training_seconds": "",
        "model_size_bytes": "",
        "random_seed": RANDOM_SEED,
        "hyperparameters_json": json.dumps(params, sort_keys=True),
        "python_version": sys.version.split()[0],
        "pandas_version": pd.__version__,
        "numpy_version": np.__version__,
        "scipy_version": scipy.__version__,
        "scikit_learn_version": sklearn.__version__,
        "joblib_version": joblib.__version__,
        "model_path": model_path.relative_to(PROJECT_ROOT).as_posix(),
        "metadata_path": metadata_path.relative_to(PROJECT_ROOT).as_posix(),
    }


def check_resume_state(hazard: str, algorithm: str, rows: dict[str, dict[str, object]]) -> bool:
    model_path, metadata_path = artifact_paths(hazard, algorithm)
    found = model_path.exists(), metadata_path.exists()
    if found == (False, False):
        return False
    if found != (True, True):
        raise ValueError(f"Incomplete existing model artifact pair: {model_path}")
    key = model_key(hazard, algorithm)
    existing = rows.get(key)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if (
        not existing
        or existing.get("status") != "success"
        or metadata.get("dataset_sha256") != DATASET_HASHES[metadata["target"]]
        or metadata.get("experiment_id") != f"phase7d_v1_{hazard}_{algorithm}"
    ):
        raise ValueError(f"Existing model does not match this Phase 7D run: {model_path}")
    return True


def train_one(
    hazard: str,
    target: str,
    algorithm: str,
    frame: pd.DataFrame,
    feature_columns: list[str],
    source_hash: str,
    rows: dict[str, dict[str, object]],
) -> None:
    model_path, metadata_path = artifact_paths(hazard, algorithm)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    key = model_key(hazard, algorithm)
    row = make_base_row(
        hazard, target, algorithm, source_hash, frame, feature_columns, model_path, metadata_path
    )
    train = frame[frame["split"].eq("train")]
    validation = frame[frame["split"].eq("validation")]
    X_train = train[feature_columns]
    y_train = train[target].to_numpy(dtype=np.int8)
    X_validation = validation[feature_columns]
    y_validation = validation[target].to_numpy(dtype=np.int8)

    append_event({
        "event": "started",
        "experiment_id": row["experiment_id"],
        "time_utc": datetime.now(timezone.utc).isoformat(),
        "train_rows": len(train),
        "validation_rows": len(validation),
    })
    started = time.perf_counter()
    warning_messages: list[str] = []
    try:
        estimator = build_estimator(algorithm)
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            if algorithm == "hist_gradient_boosting":
                sample_weight = compute_sample_weight(class_weight="balanced", y=y_train)
                estimator.fit(X_train, y_train, sample_weight=sample_weight)
            else:
                estimator.fit(X_train, y_train)
            warning_messages = [str(item.message) for item in captured]
        training_seconds = time.perf_counter() - started

        probabilities = positive_probabilities(estimator, X_validation)
        measured = calculate_metrics(y_validation, probabilities)
        temporary_model = model_path.with_name(f".{model_path.name}.tmp")
        joblib.dump(estimator, temporary_model, compress=3)
        temporary_model.replace(model_path)
        model_size = model_path.stat().st_size

        params, imbalance_strategy = hyperparameters(algorithm)
        metadata = {
            "experiment_id": row["experiment_id"],
            "status": "success",
            "hazard": hazard,
            "target": target,
            "label_scope": LABEL_SCOPE,
            "label_version": LABEL_VERSION,
            "dataset_version": DATASET_VERSION,
            "dataset_path": row["dataset_path"],
            "dataset_sha256": source_hash,
            "feature_schema_version": FEATURE_SCHEMA_VERSION,
            "feature_columns": feature_columns,
            "feature_count": len(feature_columns),
            "train_period": {"start": row["train_start"], "end": row["train_end"]},
            "train_rows": len(train),
            "train_positives": int(y_train.sum()),
            "validation_period": {"start": row["validation_start"], "end": row["validation_end"]},
            "validation_rows": len(validation),
            "validation_positives": int(y_validation.sum()),
            "test_metrics": None,
            "test_data_accessed": False,
            "parameters": params,
            "imbalance_strategy": imbalance_strategy,
            "threshold": VALIDATION_THRESHOLD,
            "validation_metrics": measured,
            "training_seconds": training_seconds,
            "model_size_bytes": model_size,
            "model_sha256": sha256(model_path),
            "random_seed": RANDOM_SEED,
            "software": {
                "python": sys.version.split()[0],
                "pandas": pd.__version__,
                "numpy": np.__version__,
                "scipy": scipy.__version__,
                "scikit_learn": sklearn.__version__,
                "joblib": joblib.__version__,
            },
            "top_features": feature_importance(estimator, feature_columns),
            "warnings": warning_messages,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "model_path": model_path.relative_to(PROJECT_ROOT).as_posix(),
        }
        atomic_json(metadata_path, metadata)

        row.update(measured)
        row.update({
            "status": "success",
            "failure": "",
            "training_seconds": training_seconds,
            "model_size_bytes": model_size,
        })
        rows[key] = row
        write_metrics(rows)
        append_event({
            "event": "completed",
            "experiment_id": row["experiment_id"],
            "time_utc": datetime.now(timezone.utc).isoformat(),
            "validation_pr_auc": measured["pr_auc_average_precision"],
            "training_seconds": training_seconds,
            "model_size_bytes": model_size,
            "warning_count": len(warning_messages),
        })
        print(
            f"  {algorithm}: PR-AUC={measured['pr_auc_average_precision']:.4f}, "
            f"ROC-AUC={measured['roc_auc']:.4f}, elapsed={training_seconds:.1f}s",
            flush=True,
        )
    except Exception as exc:
        failure = f"{type(exc).__name__}: {exc}"
        row.update({"status": "failed", "failure": failure})
        rows[key] = row
        write_metrics(rows)
        append_event({
            "event": "failed",
            "experiment_id": row["experiment_id"],
            "time_utc": datetime.now(timezone.utc).isoformat(),
            "failure": failure,
            "traceback": traceback.format_exc(),
        })
        print(f"  {algorithm}: FAILED: {failure}", flush=True)


def main() -> int:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    rows = load_existing_metrics()
    print("PHASE 7D BASELINE TRAINING: SYNTHETIC_DEVELOPMENT_ONLY", flush=True)
    print(f"Scikit-learn: {sklearn.__version__}; seed={RANDOM_SEED}; workers={MAX_WORKERS}", flush=True)
    print("Evaluation uses validation only; test rows are not read.", flush=True)

    for target, hazard in HAZARDS.items():
        frame, feature_columns, source_hash = load_train_validation(target)
        print(
            f"\n{hazard}: train={TRAIN_ROWS:,} ({int(frame.loc[frame['split'].eq('train'), target].sum())} positives), "
            f"validation={VALIDATION_ROWS:,} ({int(frame.loc[frame['split'].eq('validation'), target].sum())} positives), "
            f"features={len(feature_columns)}",
            flush=True,
        )
        for algorithm in ALGORITHMS:
            if check_resume_state(hazard, algorithm, rows):
                print(f"  {algorithm}: already completed; resuming past saved artifact", flush=True)
                continue
            train_one(hazard, target, algorithm, frame, feature_columns, source_hash, rows)
        del frame

    write_metrics(rows)
    print(f"\nMetrics: {METRICS_PATH}", flush=True)
    print(f"Models: {MODEL_ROOT}", flush=True)
    print("Test metrics: NOT RUN", flush=True)
    print("ML label scope: SYNTHETIC_DEVELOPMENT_ONLY", flush=True)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"PHASE 7D BASELINE TRAINING STOPPED: {exc}", file=sys.stderr)
        sys.exit(1)
