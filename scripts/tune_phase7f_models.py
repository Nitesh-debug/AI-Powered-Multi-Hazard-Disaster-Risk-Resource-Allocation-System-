"""Versioned Phase 7F model comparison and XGBoost/LightGBM tuning.

Only train rows are used for cross-validation and fitting. Validation rows are
used for candidate comparison and threshold selection. This module never loads
the final test portion of any Phase 7C dataset.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import warnings
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from typing import Any

import joblib
import lightgbm
import numpy as np
import pandas as pd
import scipy
import sklearn
import xgboost
from lightgbm import LGBMClassifier
from scipy.stats import loguniform, randint
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import ParameterSampler
from sklearn.utils.murmurhash import murmurhash3_32
from xgboost import XGBClassifier

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import train_phase7d_baselines as phase7d
import tune_phase7e_models as phase7e

EXPERIMENT_VERSION = "phase7f_v1"
MODEL_VERSION = "phase7f_v1"
LABEL_SCOPE = "SYNTHETIC_DEVELOPMENT_ONLY"
LABEL_VERSION = "phase7a_v1"
DATASET_VERSION = "phase7c_v1"
FEATURE_SCHEMA_VERSION = "phase5_68_shifted_weather_v1"
RANDOM_SEED = 42
N_TRIALS = 20
N_SPLITS = 3
THRESHOLDS = tuple(round(float(value), 2) for value in np.arange(0.1, 1.0, 0.1))
OUTPUT_DIR = PROJECT_ROOT / "results" / "ml" / "phase7f"
TRIAL_LOG = OUTPUT_DIR / "xgb_lgbm_temporal_cv_trials.jsonl"
CANDIDATE_METRICS_PATH = OUTPUT_DIR / "candidate_validation_metrics.csv"
THRESHOLD_PATH = OUTPUT_DIR / "selected_threshold_analysis.csv"
SELECTION_PATH = OUTPUT_DIR / "selection.json"
TEST_ATTEMPT_PATH = OUTPUT_DIR / "final_test_evaluation_attempt.json"
SELECTION_REPORT_PATH = PROJECT_ROOT / "results" / "ml" / "phase7f_model_selection.md"
MODEL_ROOT = PROJECT_ROOT / "models" / "development" / "phase7f_selected"
STAGING_MODEL_ROOT = PROJECT_ROOT / "models" / "development" / "phase7f_selected.staging"
PHASE7E_ROOT = PROJECT_ROOT / "models" / "development" / "phase7e_selected"
PHASE7D_REFERENCE_PATH = PROJECT_ROOT / "results" / "ml" / "phase7d_baseline_validation_metrics.csv"
XGB_LGBM_REFERENCE_PATH = PROJECT_ROOT / "results" / "phase7d_xgb_lgbm" / "phase7d_xgb_lgbm_validation.csv"
EXPERIMENT_MANIFEST_PATH = OUTPUT_DIR / "experiment_manifest.json"

LEGACY_ALGORITHMS = (
    "logistic_regression",
    "decision_tree",
    "random_forest",
    "extra_trees",
    "hist_gradient_boosting",
)
TUNED_ALGORITHMS = ("xgboost", "lightgbm")
HAZARD_ORDER = tuple(phase7d.HAZARDS.values())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def json_default(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return value.as_posix()
    if hasattr(value, "get_params"):
        return {
            "estimator_class": f"{type(value).__module__}.{type(value).__name__}",
            "parameters": value.get_params(deep=False),
        }
    raise TypeError(f"Cannot serialize {type(value).__name__}")


def algorithm_version(algorithm: str) -> str:
    package = {
        "logistic_regression": "scikit-learn",
        "decision_tree": "scikit-learn",
        "random_forest": "scikit-learn",
        "extra_trees": "scikit-learn",
        "hist_gradient_boosting": "scikit-learn",
        "xgboost": "xgboost",
        "lightgbm": "lightgbm",
    }[algorithm]
    return version(package)


def parameter_distributions(algorithm: str) -> dict[str, object]:
    if algorithm == "xgboost":
        return {
            "n_estimators": [150, 250, 350, 500],
            "max_depth": [2, 3, 4, 5, 6, 8],
            "learning_rate": loguniform(0.015, 0.18),
            "min_child_weight": loguniform(0.5, 20.0),
            "subsample": [0.65, 0.8, 0.9, 1.0],
            "colsample_bytree": [0.6, 0.75, 0.9, 1.0],
            "gamma": [0.0, 0.05, 0.1, 0.5, 1.0],
            "reg_alpha": loguniform(1e-5, 10.0),
            "reg_lambda": loguniform(0.1, 50.0),
        }
    if algorithm == "lightgbm":
        return {
            "n_estimators": [150, 250, 350, 500],
            "learning_rate": loguniform(0.015, 0.18),
            "num_leaves": randint(7, 65),
            "max_depth": [-1, 3, 4, 5, 6, 8, 10],
            "min_child_samples": randint(10, 81),
            "subsample": [0.65, 0.8, 0.9, 1.0],
            "colsample_bytree": [0.6, 0.75, 0.9, 1.0],
            "reg_alpha": loguniform(1e-5, 10.0),
            "reg_lambda": loguniform(0.1, 50.0),
        }
    raise ValueError(f"No tuning distribution for {algorithm}")


def deterministic_parameters(algorithm: str, hazard: str) -> list[dict[str, object]]:
    seed = murmurhash3_32(
        f"{EXPERIMENT_VERSION}:{hazard}:{algorithm}:{RANDOM_SEED}", positive=True
    )
    sampled = ParameterSampler(
        parameter_distributions(algorithm), n_iter=N_TRIALS, random_state=seed
    )
    return [dict(parameters) for parameters in sampled]


def blocked_date_splits(dates: pd.Series) -> list[tuple[np.ndarray, np.ndarray]]:
    normalized = pd.to_datetime(dates).dt.normalize()
    date_array = normalized.to_numpy(dtype="datetime64[ns]")
    unique_dates = np.unique(date_array)
    blocks = [block for block in np.array_split(unique_dates, N_SPLITS + 1) if len(block)]
    if len(blocks) != N_SPLITS + 1:
        raise ValueError("Could not create three non-empty expanding date blocks")
    folds = []
    for fold_index in range(1, len(blocks)):
        train_dates = np.concatenate(blocks[:fold_index])
        validation_dates = blocks[fold_index]
        train_rows = np.flatnonzero(np.isin(date_array, train_dates))
        validation_rows = np.flatnonzero(np.isin(date_array, validation_dates))
        if not len(train_rows) or not len(validation_rows):
            raise ValueError("Temporal cross-validation contains an empty fold")
        if date_array[train_rows].max() >= date_array[validation_rows].min():
            raise ValueError("Temporal folds overlap or are not chronological")
        folds.append((train_rows, validation_rows))
    return folds


def positive_scores(estimator: Any, features: np.ndarray) -> np.ndarray:
    class_ids = np.flatnonzero(np.asarray(estimator.classes_) == 1)
    if len(class_ids) != 1:
        raise ValueError("Estimator must expose exactly one positive class")
    scores = np.asarray(estimator.predict_proba(features)[:, int(class_ids[0])], dtype=float)
    if not np.isfinite(scores).all() or (scores < 0).any() or (scores > 1).any():
        raise ValueError("Estimator returned invalid raw model scores")
    return scores


def imbalance_ratio(labels: np.ndarray) -> float:
    positives = int(np.sum(labels == 1))
    negatives = int(np.sum(labels == 0))
    if positives == 0 or negatives == 0:
        raise ValueError("Training fold must contain both label classes")
    return negatives / positives


def build_boosted_estimator(algorithm: str, parameters: dict[str, object], labels: np.ndarray):
    ratio = imbalance_ratio(labels)
    if algorithm == "xgboost":
        return XGBClassifier(
            objective="binary:logistic",
            eval_metric="aucpr",
            tree_method="hist",
            n_jobs=1,
            random_state=RANDOM_SEED,
            scale_pos_weight=ratio,
            verbosity=0,
            **parameters,
        )
    if algorithm == "lightgbm":
        return LGBMClassifier(
            objective="binary",
            n_jobs=1,
            random_state=RANDOM_SEED,
            scale_pos_weight=ratio,
            subsample_freq=1,
            verbosity=-1,
            **parameters,
        )
    raise ValueError(f"Unsupported boosted candidate {algorithm}")


def load_completed_trials() -> dict[tuple[str, str, int], dict[str, object]]:
    completed: dict[tuple[str, str, int], dict[str, object]] = {}
    if not TRIAL_LOG.exists():
        return completed
    for line in TRIAL_LOG.read_text(encoding="utf-8").splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("event") == "trial_complete":
            key = (str(record["hazard"]), str(record["algorithm"]), int(record["trial"]))
            completed[key] = record
    return completed


def append_trial(record: dict[str, object]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with TRIAL_LOG.open("a", encoding="utf-8") as log:
        log.write(json.dumps(record, sort_keys=True, default=json_default, allow_nan=False) + "\n")
        log.flush()
        os.fsync(log.fileno())


def run_search(
    hazard: str,
    algorithm: str,
    X_train: np.ndarray,
    y_train: np.ndarray,
    train_dates: pd.Series,
    dataset_hash: str,
    completed: dict[tuple[str, str, int], dict[str, object]],
) -> list[dict[str, object]]:
    folds = blocked_date_splits(train_dates)
    results = []
    for trial_number, parameters in enumerate(deterministic_parameters(algorithm, hazard), 1):
        key = (hazard, algorithm, trial_number)
        prior = completed.get(key)
        if prior is not None:
            if prior.get("parameters") != parameters or prior.get("dataset_sha256") != dataset_hash:
                raise ValueError(f"Checkpoint does not match current inputs for {key}")
            results.append(prior)
            continue

        started = time.perf_counter()
        fold_scores: list[float] = []
        failure = ""
        try:
            for train_indexes, validation_indexes in folds:
                fold_labels = y_train[train_indexes]
                estimator = build_boosted_estimator(algorithm, parameters, fold_labels)
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    estimator.fit(X_train[train_indexes], fold_labels)
                scores = positive_scores(estimator, X_train[validation_indexes])
                fold_scores.append(float(average_precision_score(y_train[validation_indexes], scores)))
                del estimator
            mean_score = float(np.mean(fold_scores))
            std_score = float(np.std(fold_scores, ddof=0))
        except Exception as exc:
            failure = f"{type(exc).__name__}: {exc}"
            mean_score = None
            std_score = None

        record: dict[str, object] = {
            "event": "trial_complete",
            "experiment_version": EXPERIMENT_VERSION,
            "hazard": hazard,
            "algorithm": algorithm,
            "algorithm_version": algorithm_version(algorithm),
            "trial": trial_number,
            "status": "failed" if failure else "success",
            "parameters": parameters,
            "fold_count": N_SPLITS,
            "fold_average_precision": fold_scores,
            "mean_average_precision": mean_score,
            "std_average_precision": std_score,
            "fit_seconds": time.perf_counter() - started,
            "failure": failure,
            "dataset_sha256": dataset_hash,
            "feature_count": 68,
            "train_rows": int(len(y_train)),
            "train_positives": int(y_train.sum()),
            "random_seed": RANDOM_SEED,
            "cv_method": "expanding, non-overlapping target-date folds; district-date cohorts kept together",
            "imbalance_method": "scale_pos_weight computed from each fitting fold only",
            "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        append_trial(record)
        completed[key] = record
        results.append(record)
    if not any(record["status"] == "success" for record in results):
        raise RuntimeError(f"All {algorithm} trials failed for {hazard}")
    return results


def metric_bundle(labels: np.ndarray, scores: np.ndarray, threshold: float) -> dict[str, float | int]:
    predictions = scores >= threshold
    tn, fp, fn, tp = (int(value) for value in confusion_matrix(labels, predictions, labels=[0, 1]).ravel())
    return {
        "threshold": float(threshold),
        "precision": float(precision_score(labels, predictions, zero_division=0)),
        "recall": float(recall_score(labels, predictions, zero_division=0)),
        "f1": float(f1_score(labels, predictions, zero_division=0)),
        "average_precision": float(average_precision_score(labels, scores)),
        "roc_auc": float(roc_auc_score(labels, scores)),
        "brier_score": float(brier_score_loss(labels, scores)),
        "true_negative": tn,
        "false_positive": fp,
        "false_negative": fn,
        "true_positive": tp,
        "false_alarm_rate": float(fp / (fp + tn)) if fp + tn else 0.0,
    }


def choose_threshold(labels: np.ndarray, scores: np.ndarray) -> tuple[dict[str, object], list[dict[str, object]]]:
    rows = []
    for threshold in THRESHOLDS:
        rows.append({"threshold": threshold, **metric_bundle(labels, scores, threshold)})
    selected = max(
        rows,
        key=lambda row: (
            float(row["f1"]),
            float(row["precision"]),
            float(row["recall"]),
            -float(row["false_alarm_rate"]),
            -float(row["threshold"]),
        ),
    )
    return selected, rows


def reference_metrics() -> dict[tuple[str, str], dict[str, object]]:
    legacy = pd.read_csv(PHASE7D_REFERENCE_PATH)
    boosted = pd.read_csv(XGB_LGBM_REFERENCE_PATH)
    references: dict[tuple[str, str], dict[str, object]] = {}
    for row in legacy.itertuples(index=False):
        if row.status != "success":
            continue
        references[(str(row.hazard), str(row.algorithm))] = {
            "experiment": "phase7d_v1",
            "average_precision": float(row.pr_auc_average_precision),
            "roc_auc": float(row.roc_auc),
        }
    for row in boosted.itertuples(index=False):
        references[(str(row.hazard), str(row.algorithm))] = {
            "experiment": str(row.experiment),
            "average_precision": float(row.average_precision),
            "roc_auc": float(row.roc_auc),
        }
    expected = {
        (hazard, algorithm)
        for hazard in HAZARD_ORDER
        for algorithm in (*LEGACY_ALGORITHMS, *TUNED_ALGORITHMS)
    }
    if references.keys() != expected:
        missing = sorted(expected - references.keys())
        extra = sorted(references.keys() - expected)
        raise ValueError(f"Preserved validation reference matrix mismatch; missing={missing}, extra={extra}")
    return references


def make_candidate_row(
    *,
    hazard: str,
    candidate_id: str,
    algorithm: str,
    estimator: Any,
    parameter_source: str,
    parameters: dict[str, object],
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_validation: np.ndarray,
    y_validation: np.ndarray,
    dataset_hash: str,
    train: pd.DataFrame,
    validation: pd.DataFrame,
    cv_mean: float | None,
    cv_std: float | None,
    cv_trial_count: int,
    historical_reference: dict[str, object] | None = None,
) -> dict[str, object]:
    started = time.perf_counter()
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        estimator.fit(X_train, y_train)
    fit_seconds = time.perf_counter() - started
    validation_scores = positive_scores(estimator, X_validation)
    metrics = metric_bundle(y_validation, validation_scores, 0.5)
    row: dict[str, object] = {
        "experiment_version": EXPERIMENT_VERSION,
        "hazard": hazard,
        "candidate_id": candidate_id,
        "algorithm": algorithm,
        "algorithm_version": algorithm_version(algorithm),
        "parameter_source": parameter_source,
        "parameters_json": json.dumps(parameters, sort_keys=True, default=json_default),
        "dataset_version": DATASET_VERSION,
        "dataset_sha256": dataset_hash,
        "label_scope": LABEL_SCOPE,
        "label_version": LABEL_VERSION,
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "feature_count": int(X_train.shape[1]),
        "train_rows": int(len(train)),
        "train_positives": int(y_train.sum()),
        "train_negatives": int(len(y_train) - y_train.sum()),
        "train_start": train["target_date"].min().strftime("%Y-%m-%d"),
        "train_end": train["target_date"].max().strftime("%Y-%m-%d"),
        "validation_rows": int(len(validation)),
        "validation_positives": int(y_validation.sum()),
        "validation_negatives": int(len(y_validation) - y_validation.sum()),
        "validation_start": validation["target_date"].min().strftime("%Y-%m-%d"),
        "validation_end": validation["target_date"].max().strftime("%Y-%m-%d"),
        "cv_trial_count": int(cv_trial_count),
        "cv_success_count": 0,
        "cv_fit_seconds_total": None,
        "cv_mean_average_precision": cv_mean,
        "cv_std_average_precision": cv_std,
        "validation_average_precision": metrics["average_precision"],
        "validation_roc_auc": metrics["roc_auc"],
        "validation_precision_at_0_5": metrics["precision"],
        "validation_recall_at_0_5": metrics["recall"],
        "validation_f1_at_0_5": metrics["f1"],
        "validation_false_alarm_rate_at_0_5": metrics["false_alarm_rate"],
        "validation_brier_score": metrics["brier_score"],
        "validation_true_negative_at_0_5": metrics["true_negative"],
        "validation_false_positive_at_0_5": metrics["false_positive"],
        "validation_false_negative_at_0_5": metrics["false_negative"],
        "validation_true_positive_at_0_5": metrics["true_positive"],
        "prior_reference_experiment": (historical_reference or {}).get("experiment"),
        "prior_reference_validation_ap": (historical_reference or {}).get("average_precision"),
        "prior_reference_validation_roc_auc": (historical_reference or {}).get("roc_auc"),
        "fit_seconds": fit_seconds,
        "warning_count": len(captured),
        "calibrated": False,
        "test_rows_read": False,
    }
    return {
        "row": row,
        "estimator": estimator,
        "validation_scores": validation_scores,
        "validation_metrics_at_0_5": metrics,
        "parameters": parameters,
    }


def ensure_manifest() -> None:
    manifest = {
        "experiment_version": EXPERIMENT_VERSION,
        "model_version": MODEL_VERSION,
        "label_scope": LABEL_SCOPE,
        "label_version": LABEL_VERSION,
        "dataset_version": DATASET_VERSION,
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "hazards": list(HAZARD_ORDER),
        "legacy_algorithms": list(LEGACY_ALGORITHMS),
        "tuned_algorithms": list(TUNED_ALGORITHMS),
        "candidate_set": [
            *[f"phase7d_{name}" for name in LEGACY_ALGORITHMS],
            "phase7e_incumbent_refit",
            *[f"phase7f_tuned_{name}" for name in TUNED_ALGORITHMS],
        ],
        "trials_per_tuned_candidate": N_TRIALS,
        "expanding_date_folds": N_SPLITS,
        "thresholds": list(THRESHOLDS),
        "random_seed": RANDOM_SEED,
        "test_data_accessed": False,
        "software": {
            "python": sys.version.split()[0],
            "pandas": pd.__version__,
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "scikit_learn": sklearn.__version__,
            "joblib": joblib.__version__,
            "xgboost": xgboost.__version__,
            "lightgbm": lightgbm.__version__,
        },
    }
    if EXPERIMENT_MANIFEST_PATH.exists():
        existing = json.loads(EXPERIMENT_MANIFEST_PATH.read_text(encoding="utf-8"))
        for key, value in manifest.items():
            if existing.get(key) != value:
                raise ValueError(f"Phase 7F checkpoint manifest mismatch for {key}")
    else:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        EXPERIMENT_MANIFEST_PATH.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )


def validate_existing_references() -> None:
    for path in (PHASE7D_REFERENCE_PATH, XGB_LGBM_REFERENCE_PATH):
        if not path.is_file():
            raise FileNotFoundError(f"Required preserved validation reference is missing: {path}")
    if not PHASE7E_ROOT.is_dir():
        raise FileNotFoundError(f"Phase 7E incumbent models are missing: {PHASE7E_ROOT}")
    if MODEL_ROOT.exists() or STAGING_MODEL_ROOT.exists():
        raise FileExistsError(f"Refusing to overwrite a Phase 7F model registry: {MODEL_ROOT}")
    if any(path.exists() for path in (
        CANDIDATE_METRICS_PATH,
        THRESHOLD_PATH,
        SELECTION_PATH,
        SELECTION_REPORT_PATH,
    )):
        raise FileExistsError("Phase 7F selection artifacts already exist; refusing to overwrite")


def select_models() -> tuple[list[dict[str, object]], dict[str, dict[str, object]], list[dict[str, object]]]:
    ensure_manifest()
    validate_existing_references()
    references = reference_metrics()
    completed = load_completed_trials()
    all_rows: list[dict[str, object]] = []
    selected_by_hazard: dict[str, dict[str, object]] = {}
    threshold_rows: list[dict[str, object]] = []

    for target, hazard in phase7d.HAZARDS.items():
        frame, features, dataset_hash = phase7d.load_train_validation(target)
        train = frame.loc[frame["split"].eq("train")].copy()
        validation = frame.loc[frame["split"].eq("validation")].copy()
        X_train = train[features].to_numpy(dtype=np.float32)
        y_train = train[target].to_numpy(dtype=np.int8)
        X_validation = validation[features].to_numpy(dtype=np.float32)
        y_validation = validation[target].to_numpy(dtype=np.int8)
        train_dates = train["target_date"]
        candidates: list[dict[str, object]] = []

        print(f"\n{hazard}: train={len(train):,}, validation={len(validation):,}; test rows not loaded", flush=True)

        incumbent_metadata = json.loads(
            (PHASE7E_ROOT / hazard / "metadata.json").read_text(encoding="utf-8")
        )
        if (
            incumbent_metadata.get("model_version") != "phase7e_v1"
            or incumbent_metadata.get("hazard") != hazard
            or incumbent_metadata.get("label_scope") != LABEL_SCOPE
            or incumbent_metadata.get("label_version") != LABEL_VERSION
            or incumbent_metadata.get("dataset_sha256") != dataset_hash
            or len(incumbent_metadata.get("feature_columns", [])) != 68
        ):
            raise ValueError(f"Phase 7E incumbent metadata is incompatible for {hazard}")

        for algorithm in LEGACY_ALGORITHMS:
            estimator = phase7d.build_estimator(algorithm)
            parameters = estimator.get_params(deep=True)
            candidate = make_candidate_row(
                hazard=hazard,
                candidate_id=f"phase7d_{algorithm}",
                algorithm=algorithm,
                estimator=estimator,
                parameter_source="phase7d_v1 fixed baseline parameters, refit on train under phase7f software",
                parameters=parameters,
                X_train=X_train,
                y_train=y_train,
                X_validation=X_validation,
                y_validation=y_validation,
                dataset_hash=dataset_hash,
                train=train,
                validation=validation,
                cv_mean=None,
                cv_std=None,
                cv_trial_count=0,
                historical_reference=references.get((hazard, algorithm)),
            )
            candidates.append(candidate)
            print(
                f"  {candidate['row']['candidate_id']}: validation AP={candidate['row']['validation_average_precision']:.5f}",
                flush=True,
            )

        incumbent_algorithm = str(incumbent_metadata["selected_algorithm"])
        incumbent = make_candidate_row(
            hazard=hazard,
            candidate_id="phase7e_incumbent_refit",
            algorithm=incumbent_algorithm,
            estimator=phase7e.build_estimator(incumbent_algorithm, incumbent_metadata["selected_parameters"]),
            parameter_source="phase7e_v1 frozen selected parameters, refit on train under phase7f software",
            parameters=incumbent_metadata["selected_parameters"],
            X_train=X_train,
            y_train=y_train,
            X_validation=X_validation,
            y_validation=y_validation,
            dataset_hash=dataset_hash,
            train=train,
            validation=validation,
            cv_mean=None,
            cv_std=None,
            cv_trial_count=0,
            historical_reference={
                "experiment": "phase7e_v1",
                "average_precision": incumbent_metadata["validation_metrics_at_0_5"]["validation_average_precision"],
                "roc_auc": incumbent_metadata["validation_metrics_at_0_5"]["validation_roc_auc"],
            },
        )
        candidates.append(incumbent)
        print(
            f"  phase7e_incumbent_refit: validation AP={incumbent['row']['validation_average_precision']:.5f}",
            flush=True,
        )

        for algorithm in TUNED_ALGORITHMS:
            trial_results = run_search(
                hazard,
                algorithm,
                X_train,
                y_train,
                train_dates,
                dataset_hash,
                completed,
            )
            successful = [row for row in trial_results if row["status"] == "success"]
            best_trial = max(
                successful,
                key=lambda row: (
                    float(row["mean_average_precision"]),
                    -float(row["std_average_precision"]),
                    -int(row["trial"]),
                ),
            )
            parameters = dict(best_trial["parameters"])
            estimator = build_boosted_estimator(algorithm, parameters, y_train)
            candidate = make_candidate_row(
                hazard=hazard,
                candidate_id=f"phase7f_tuned_{algorithm}",
                algorithm=algorithm,
                estimator=estimator,
                parameter_source="best training-only expanding-date CV average precision from deterministic randomized search",
                parameters=parameters,
                X_train=X_train,
                y_train=y_train,
                X_validation=X_validation,
                y_validation=y_validation,
                dataset_hash=dataset_hash,
                train=train,
                validation=validation,
                cv_mean=float(best_trial["mean_average_precision"]),
                cv_std=float(best_trial["std_average_precision"]),
                cv_trial_count=len(trial_results),
                historical_reference=references.get((hazard, algorithm)),
            )
            candidate["row"]["cv_success_count"] = len(successful)
            candidate["row"]["cv_fit_seconds_total"] = float(
                sum(float(row["fit_seconds"]) for row in trial_results)
            )
            candidate["row"]["best_cv_trial"] = int(best_trial["trial"])
            candidate["row"]["best_cv_fold_average_precision"] = json.dumps(best_trial["fold_average_precision"])
            candidates.append(candidate)
            print(
                f"  {algorithm}: CV AP={best_trial['mean_average_precision']:.5f} +/- "
                f"{best_trial['std_average_precision']:.5f}; validation AP="
                f"{candidate['row']['validation_average_precision']:.5f}",
                flush=True,
            )

        # AP is primary; ROC-AUC, FAR at 0.50, then candidate ID settle exact ties.
        selected = max(
            candidates,
            key=lambda item: (
                float(item["row"]["validation_average_precision"]),
                float(item["row"]["validation_roc_auc"]),
                -float(item["row"]["validation_false_alarm_rate_at_0_5"]),
                str(item["row"]["candidate_id"]),
            ),
        )
        threshold, rows = choose_threshold(y_validation, selected["validation_scores"])
        threshold_rows.extend(
            {"hazard": hazard, "target": target, **row} for row in rows
        )
        for candidate in candidates:
            candidate["row"]["selected_for_registry"] = candidate is selected
            candidate["row"]["selected_validation_threshold"] = (
                float(threshold["threshold"]) if candidate is selected else None
            )
        selected_by_hazard[hazard] = {
            **selected,
            "target": target,
            "threshold_selection": threshold,
            "threshold_analysis": rows,
            "dataset_hash": dataset_hash,
            "feature_columns": features,
            "train": train,
            "validation": validation,
            "train_labels": y_train,
            "validation_labels": y_validation,
            "cv_method": (
                "20 deterministic randomized configurations per XGBoost/LightGBM candidate; "
                "3 expanding date-block folds on train only; all district rows for a date stay together"
            ),
        }
        all_rows.extend(candidate["row"] for candidate in candidates)
        print(
            f"  selected {selected['row']['candidate_id']} at validation threshold "
            f"{threshold['threshold']:.2f}; F1={threshold['f1']:.4f}",
            flush=True,
        )
        del frame, X_train, X_validation, candidates

    return all_rows, selected_by_hazard, threshold_rows


def save_selected_models(selected: dict[str, dict[str, object]]) -> None:
    STAGING_MODEL_ROOT.mkdir(parents=True, exist_ok=False)
    created_at = datetime.now(timezone.utc).isoformat()
    for hazard in HAZARD_ORDER:
        item = selected[hazard]
        directory = STAGING_MODEL_ROOT / hazard
        directory.mkdir()
        model_path = directory / "model.joblib"
        metadata_path = directory / "metadata.json"
        temporary_model = model_path.with_name(".model.joblib.tmp")
        joblib.dump(item["estimator"], temporary_model, compress=3)
        temporary_model.replace(model_path)
        metrics_at_half = item["validation_metrics_at_0_5"]
        metadata = {
            "model_version": MODEL_VERSION,
            "experiment_version": EXPERIMENT_VERSION,
            "hazard": hazard,
            "target": item["target"],
            "selected_candidate_id": item["row"]["candidate_id"],
            "selected_algorithm": item["row"]["algorithm"],
            "algorithm_version": item["row"]["algorithm_version"],
            "selected_parameters": item["parameters"],
            "parameter_source": item["row"]["parameter_source"],
            "feature_schema_version": FEATURE_SCHEMA_VERSION,
            "feature_columns": item["feature_columns"],
            "feature_count": len(item["feature_columns"]),
            "dataset_version": DATASET_VERSION,
            "dataset_sha256": item["dataset_hash"],
            "label_scope": LABEL_SCOPE,
            "label_type": "synthetic_development",
            "label_version": LABEL_VERSION,
            "training_period": {
                "split": "train",
                "start": item["train"]["target_date"].min().strftime("%Y-%m-%d"),
                "end": item["train"]["target_date"].max().strftime("%Y-%m-%d"),
                "rows": len(item["train"]),
                "positive_rows": int(item["train_labels"].sum()),
                "negative_rows": int(len(item["train_labels"]) - item["train_labels"].sum()),
            },
            "validation_period": {
                "split": "validation",
                "start": item["validation"]["target_date"].min().strftime("%Y-%m-%d"),
                "end": item["validation"]["target_date"].max().strftime("%Y-%m-%d"),
                "rows": len(item["validation"]),
                "positive_rows": int(item["validation_labels"].sum()),
                "negative_rows": int(len(item["validation_labels"]) - item["validation_labels"].sum()),
            },
            "selection_method": (
                "Highest validation average precision across five Phase 7D baselines, "
                "the Phase 7E tuned incumbent refit, XGBoost, and LightGBM; ROC-AUC, "
                "false-alarm-rate-at-0.50, then candidate ID are deterministic tie-breakers"
            ),
            "cross_validation": {
                "method": item["cv_method"],
                "best_candidate_mean_average_precision": item["row"]["cv_mean_average_precision"],
                "best_candidate_std_average_precision": item["row"]["cv_std_average_precision"],
                "trial_count_per_tuned_candidate": N_TRIALS,
                "fold_count": N_SPLITS,
            },
            "validation_metrics_at_0_5": {
                "validation_average_precision": metrics_at_half["average_precision"],
                "validation_roc_auc": metrics_at_half["roc_auc"],
                "validation_precision": metrics_at_half["precision"],
                "validation_recall": metrics_at_half["recall"],
                "validation_f1": metrics_at_half["f1"],
                "validation_false_alarm_rate": metrics_at_half["false_alarm_rate"],
                "validation_brier_score": metrics_at_half["brier_score"],
            },
            "threshold_selection": {
                "split": "validation",
                "method": "maximize F1 over thresholds 0.10 through 0.90 by 0.10; ties prefer precision, recall, lower false-alarm rate, then lower threshold",
                "selected_threshold": float(item["threshold_selection"]["threshold"]),
                "metrics": item["threshold_selection"],
            },
            "calibration": {
                "method": "none",
                "calibrated": False,
                "score_semantics": "raw uncalibrated estimator score; not a calibrated probability",
            },
            "training_date_utc": created_at,
            "random_seed": RANDOM_SEED,
            "software": {
                "python": sys.version.split()[0],
                "pandas": pd.__version__,
                "numpy": np.__version__,
                "scipy": scipy.__version__,
                "scikit_learn": sklearn.__version__,
                "joblib": joblib.__version__,
                "xgboost": xgboost.__version__,
                "lightgbm": lightgbm.__version__,
            },
            "model_path": (MODEL_ROOT / hazard / "model.joblib").relative_to(PROJECT_ROOT).as_posix(),
            "metadata_path": (MODEL_ROOT / hazard / "metadata.json").relative_to(PROJECT_ROOT).as_posix(),
            "model_size_bytes": model_path.stat().st_size,
            "model_sha256": sha256(model_path),
            "test_period": {
                "split": "test",
                "start": "2023-01-01",
                "end": "2025-10-31",
                "evaluation_status": "pending_final_evaluation",
            },
            "test_data_accessed": False,
            "test_metrics": None,
            "test_evaluation_artifact": "results/ml/phase7f_final_test_evaluation.md",
            "label_warning": "SYNTHETIC_DEVELOPMENT_ONLY; does not represent verified disaster occurrence or real-world forecasting skill",
        }
        metadata_temp = metadata_path.with_name(".metadata.json.tmp")
        metadata_temp.write_text(
            json.dumps(metadata, indent=2, sort_keys=True, default=json_default, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        metadata_temp.replace(metadata_path)
    STAGING_MODEL_ROOT.replace(MODEL_ROOT)


def write_selection_report(
    candidate_rows: list[dict[str, object]], selected: dict[str, dict[str, object]]
) -> None:
    lines = [
        "# Phase 7F v1 Model Selection (Validation Only)",
        "",
        "**SYNTHETIC_DEVELOPMENT_ONLY**",
        "",
        "This is a new versioned experiment. Existing Phase 7D, Phase 7D XGBoost/LightGBM, and Phase 7E reports/artifacts are preserved.",
        "",
        "## Method",
        "",
        "- All data loading uses the Phase 7D hash-checked train/validation-prefix loader; test rows are not loaded during tuning or selection.",
        "- Five Phase 7D algorithms are refit with their existing baseline configurations. The Phase 7E selected incumbent is also refit with its frozen parameters for each hazard.",
        f"- XGBoost and LightGBM each receive {N_TRIALS} deterministic randomized configurations per hazard; configurations are scored with {N_SPLITS} expanding target-date folds inside training.",
        "- Entire district-date cohorts remain in the same temporal fold. `scale_pos_weight` is computed from each fitting fold (or the train split for final candidate fit), never from validation/test labels.",
        "- The candidate comparison metric is validation average precision. ROC-AUC, false-alarm rate at 0.50, then candidate ID are deterministic tie-breakers.",
        "- The eight candidates are five fixed Phase 7D baselines, one Phase 7E selected incumbent refit, and tuned XGBoost and LightGBM. Prior Phase 7D/7E validation metrics are retained as references; the Phase 7F comparison uses fresh fits on the same train/validation splits.",
        "- Temporal evaluation retains the same 20 districts in later periods. Spatial transfer to unseen districts is not tested; correlated district weather can still limit generalization.",
        "- The same chronological test interval was already evaluated for Phase 7E in an earlier version. Phase 7F will not use those prior test metrics for selection, but its evaluation is not a project-wide pristine holdout.",
        "- Thresholds are selected on validation only by maximum F1 over 0.10 through 0.90. No calibration is fitted; estimator scores remain raw and uncalibrated.",
        "- Every candidate is SYNTHETIC_DEVELOPMENT_ONLY (`phase7a_v1`); these experiments do not measure verified disaster forecasting skill.",
        "",
        "## Candidate Results",
        "",
        "| Hazard | Candidate | Algorithm | Prior AP reference | CV AP mean (SD) | Phase 7F validation AP | ROC-AUC | F1 at 0.50 | FAR at 0.50 | Fit seconds | Selected |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    selected_ids = {hazard: item["row"]["candidate_id"] for hazard, item in selected.items()}
    for row in sorted(candidate_rows, key=lambda item: (str(item["hazard"]), str(item["candidate_id"]))):
        cv = "not tuned"
        if row["cv_mean_average_precision"] is not None:
            cv = f"{float(row['cv_mean_average_precision']):.4f} ({float(row['cv_std_average_precision']):.4f})"
        prior_ap = "n/a"
        if row["prior_reference_validation_ap"] is not None:
            prior_ap = f"{float(row['prior_reference_validation_ap']):.4f}"
        winner = str(row["candidate_id"]) == selected_ids[str(row["hazard"])]
        lines.append(
            f"| {row['hazard']} | {row['candidate_id']} | {row['algorithm']} | {prior_ap} | {cv} | "
            f"{float(row['validation_average_precision']):.4f} | {float(row['validation_roc_auc']):.4f} | "
            f"{float(row['validation_f1_at_0_5']):.4f} | {float(row['validation_false_alarm_rate_at_0_5']):.4f} | "
            f"{float(row['fit_seconds']):.2f} | {'YES' if winner else 'no'} |"
        )
    lines.extend([
        "",
        "## Selected Validation Operating Points",
        "",
        "| Hazard | Selected candidate | Threshold | Precision | Recall | F1 | FAR | AP | ROC-AUC | Brier |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ])
    for hazard in HAZARD_ORDER:
        item = selected[hazard]
        metrics = item["threshold_selection"]
        lines.append(
            f"| {hazard} | {item['row']['candidate_id']} | {float(metrics['threshold']):.2f} | "
            f"{float(metrics['precision']):.4f} | {float(metrics['recall']):.4f} | "
            f"{float(metrics['f1']):.4f} | {float(metrics['false_alarm_rate']):.4f} | "
            f"{float(metrics['average_precision']):.4f} | {float(metrics['roc_auc']):.4f} | "
            f"{float(metrics['brier_score']):.4f} |"
        )
    lines.extend([
        "",
        "## Artifacts",
        "",
        "- Trial configurations and fold scores: `results/ml/phase7f/xgb_lgbm_temporal_cv_trials.jsonl`.",
        "- All candidate metrics: `results/ml/phase7f/candidate_validation_metrics.csv`.",
        "- Selected validation threshold analysis: `results/ml/phase7f/selected_threshold_analysis.csv`.",
        "- Versioned model registry: `models/development/phase7f_selected/`.",
        "- Test rows read: **No**. Final test evaluation is a separate one-time command after this selection is frozen.",
        "",
    ])
    SELECTION_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    if SELECTION_REPORT_PATH.exists():
        raise FileExistsError(f"Refusing to overwrite {SELECTION_REPORT_PATH}")
    SELECTION_REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    print(f"Phase 7F: {N_TRIALS} trials x {N_SPLITS} temporal folds per XGBoost/LightGBM candidate", flush=True)
    candidate_rows, selected, thresholds = select_models()
    if len(candidate_rows) != len(HAZARD_ORDER) * (len(LEGACY_ALGORITHMS) + len(TUNED_ALGORITHMS) + 1):
        raise ValueError("Phase 7F candidate matrix is incomplete")
    save_selected_models(selected)
    if CANDIDATE_METRICS_PATH.exists() or THRESHOLD_PATH.exists() or SELECTION_PATH.exists():
        raise FileExistsError("Refusing to overwrite Phase 7F selection outputs")
    pd.DataFrame(candidate_rows).to_csv(CANDIDATE_METRICS_PATH, index=False, encoding="utf-8")
    pd.DataFrame(thresholds).to_csv(THRESHOLD_PATH, index=False, encoding="utf-8")
    selection = {
        "experiment_version": EXPERIMENT_VERSION,
        "model_version": MODEL_VERSION,
        "label_scope": LABEL_SCOPE,
        "label_version": LABEL_VERSION,
        "dataset_version": DATASET_VERSION,
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "selection_metric": "validation_average_precision",
        "test_data_accessed": False,
        "selected": {
            hazard: {
                "candidate_id": item["row"]["candidate_id"],
                "algorithm": item["row"]["algorithm"],
                "validation_average_precision": item["row"]["validation_average_precision"],
                "validation_roc_auc": item["row"]["validation_roc_auc"],
                "threshold": item["threshold_selection"]["threshold"],
                "threshold_metrics": item["threshold_selection"],
            }
            for hazard, item in selected.items()
        },
    }
    SELECTION_PATH.write_text(
        json.dumps(selection, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )
    write_selection_report(candidate_rows, selected)
    manifest = json.loads(EXPERIMENT_MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest["selection_status"] = "frozen_validation_only"
    manifest["candidate_count"] = len(candidate_rows)
    manifest["selected_candidates"] = {
        hazard: item["row"]["candidate_id"] for hazard, item in selected.items()
    }
    manifest["dataset_sha256"] = {
        hazard: selected[hazard]["dataset_hash"] for hazard in HAZARD_ORDER
    }
    EXPERIMENT_MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"Selection frozen; test rows read: No; report: {SELECTION_REPORT_PATH}", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError, AssertionError, RuntimeError) as exc:
        print(f"PHASE 7F MODEL SELECTION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
