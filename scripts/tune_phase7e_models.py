"""Bounded temporal random search and validation-only model selection."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import scipy
import sklearn
from scipy.stats import loguniform, randint
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
from sklearn.utils.murmurhash import murmurhash3_32
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import ParameterSampler

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.train_phase7d_baselines import (
    DATASET_HASHES,
    HAZARDS,
    LABEL_SCOPE,
    LABEL_VERSION,
    RANDOM_SEED,
    dataset_path,
    load_train_validation,
    positive_probabilities,
)


MODEL_ROOT = PROJECT_ROOT / "models" / "development" / "phase7e_selected"
RESULTS_DIR = PROJECT_ROOT / "results" / "ml"
PHASE_RESULTS = RESULTS_DIR / "phase7e"
TRIAL_LOG = PHASE_RESULTS / "temporal_cv_trials.jsonl"
CANDIDATE_METRICS_PATH = PHASE_RESULTS / "candidate_validation_metrics.csv"
THRESHOLD_PATH = PHASE_RESULTS / "selected_threshold_analysis.csv"
REPORT_PATH = RESULTS_DIR / "phase7e_model_selection.md"

N_ITER = 20
N_SPLITS = 3
N_JOBS = max(1, min(4, os.cpu_count() or 1))
THRESHOLDS = tuple(round(value, 2) for value in np.arange(0.1, 1.0, 0.1))
VALIDATION_FEATURE_SCHEMA = "phase5_68_shifted_weather_v1"
DATASET_VERSION = "phase7c_v1"
MODEL_VERSION = "phase7e_v1"

CANDIDATES = {
    "flood": ["random_forest", "hist_gradient_boosting"],
    "heavy_rain": ["logistic_regression", "extra_trees"],
    "landslide": ["extra_trees", "logistic_regression"],
    "heatwave": ["extra_trees", "hist_gradient_boosting"],
    "coldwave": ["extra_trees", "random_forest"],
    "windstorm": ["extra_trees", "random_forest"],
}


def append_jsonl(path: Path, record: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as log:
        log.write(json.dumps(record, sort_keys=True, default=str) + "\n")
        log.flush()
        os.fsync(log.fileno())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def candidate_distributions(algorithm: str) -> dict[str, object]:
    if algorithm == "logistic_regression":
        return {
            "logisticregression__C": loguniform(0.01, 100.0),
            "logisticregression__class_weight": [None, "balanced"],
            "logisticregression__solver": ["lbfgs", "saga"],
            "logisticregression__max_iter": [1500, 2500],
        }
    if algorithm == "random_forest":
        return {
            "n_estimators": [150, 250, 350],
            "max_depth": [None, 8, 12, 16, 24],
            "min_samples_split": randint(2, 22),
            "min_samples_leaf": randint(2, 32),
            "max_features": ["sqrt", "log2", 0.4, 0.7],
            "class_weight": [None, "balanced", "balanced_subsample"],
        }
    if algorithm == "extra_trees":
        return {
            "n_estimators": [150, 250, 350],
            "max_depth": [None, 8, 12, 16, 24],
            "min_samples_split": randint(2, 22),
            "min_samples_leaf": randint(2, 32),
            "max_features": ["sqrt", "log2", 0.4, 0.7],
            "class_weight": [None, "balanced"],
        }
    if algorithm == "hist_gradient_boosting":
        return {
            "learning_rate": loguniform(0.025, 0.2),
            "max_iter": randint(80, 241),
            "max_leaf_nodes": randint(7, 33),
            "max_depth": [None, 3, 5, 8],
            "min_samples_leaf": randint(10, 61),
            "l2_regularization": loguniform(0.001, 10.0),
            "class_weight": [None, "balanced"],
        }
    raise ValueError(f"No tuning distributions for {algorithm}")


def build_estimator(algorithm: str, parameters: dict[str, object]):
    if algorithm == "logistic_regression":
        base = make_pipeline(StandardScaler(), LogisticRegression(random_state=RANDOM_SEED))
        base.set_params(**parameters)
        return base
    if algorithm == "random_forest":
        defaults = {"random_state": RANDOM_SEED, "n_jobs": N_JOBS}
        return RandomForestClassifier(**defaults, **parameters)
    if algorithm == "extra_trees":
        defaults = {"random_state": RANDOM_SEED, "n_jobs": N_JOBS}
        return ExtraTreesClassifier(**defaults, **parameters)
    if algorithm == "hist_gradient_boosting":
        defaults = {"random_state": RANDOM_SEED, "early_stopping": False}
        return HistGradientBoostingClassifier(**defaults, **parameters)
    raise ValueError(f"Unsupported candidate algorithm: {algorithm}")


def blocked_date_splits(dates: pd.Series) -> list[tuple[np.ndarray, np.ndarray]]:
    unique_dates = np.array(sorted(pd.to_datetime(dates).dt.normalize().unique()))
    date_blocks = [block for block in np.array_split(unique_dates, N_SPLITS + 1) if len(block)]
    if len(date_blocks) != N_SPLITS + 1:
        raise ValueError("Could not create three non-empty temporal validation blocks")
    date_array = pd.to_datetime(dates).dt.normalize().to_numpy()
    splits = []
    for index in range(1, len(date_blocks)):
        train_dates = np.concatenate(date_blocks[:index])
        valid_dates = date_blocks[index]
        train_indexes = np.flatnonzero(np.isin(date_array, train_dates))
        valid_indexes = np.flatnonzero(np.isin(date_array, valid_dates))
        if not len(train_indexes) or not len(valid_indexes):
            raise ValueError("Temporal CV produced an empty fold")
        if date_array[train_indexes].max() >= date_array[valid_indexes].min():
            raise ValueError("Temporal CV dates overlap or are out of order")
        splits.append((train_indexes, valid_indexes))
    return splits


def deterministic_trial_parameters(algorithm: str, hazard: str) -> list[dict[str, object]]:
    seed = murmurhash3_32(f"{hazard}:{algorithm}:{RANDOM_SEED}", positive=True)
    sampled = list(ParameterSampler(candidate_distributions(algorithm), n_iter=N_ITER, random_state=seed))
    return [dict(item) for item in sampled]


def load_trial_checkpoint() -> dict[tuple[str, str, int], dict[str, object]]:
    completed: dict[tuple[str, str, int], dict[str, object]] = {}
    if not TRIAL_LOG.exists():
        return completed
    for line in TRIAL_LOG.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("event") == "trial_complete":
            key = (row["hazard"], row["algorithm"], int(row["trial"]))
            completed[key] = row
    return completed


def run_trials(
    hazard: str,
    algorithm: str,
    X: np.ndarray,
    y: np.ndarray,
    dates: pd.Series,
    completed: dict[tuple[str, str, int], dict[str, object]],
) -> list[dict[str, object]]:
    folds = blocked_date_splits(dates)
    parameter_list = deterministic_trial_parameters(algorithm, hazard)
    results: list[dict[str, object]] = []
    for number, parameters in enumerate(parameter_list, start=1):
        key = (hazard, algorithm, number)
        if key in completed:
            results.append(completed[key])
            print(f"    trial {number}/{N_ITER}: checkpoint reused", flush=True)
            continue
        started = time.perf_counter()
        fold_scores: list[float] = []
        failure = ""
        try:
            for train_indexes, validation_indexes in folds:
                estimator = build_estimator(algorithm, parameters)
                with warnings.catch_warnings(record=True):
                    warnings.simplefilter("ignore")
                    estimator.fit(X[train_indexes], y[train_indexes])
                probabilities = positive_probabilities(estimator, X[validation_indexes])
                fold_scores.append(float(average_precision_score(y[validation_indexes], probabilities)))
                del estimator
            mean_score = float(np.mean(fold_scores))
            deviation = float(np.std(fold_scores, ddof=0))
        except Exception as exc:
            failure = f"{type(exc).__name__}: {exc}"
            mean_score = float("nan")
            deviation = float("nan")
        record = {
            "event": "trial_complete",
            "hazard": hazard,
            "algorithm": algorithm,
            "trial": number,
            "status": "failed" if failure else "success",
            "parameters": parameters,
            "fold_average_precision": fold_scores,
            "mean_average_precision": mean_score,
            "std_average_precision": deviation,
            "fit_seconds": time.perf_counter() - started,
            "failure": failure,
            "random_seed": RANDOM_SEED,
            "cv_kind": "expanding date-blocked; entire district-date cohorts kept together",
            "logged_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        append_jsonl(TRIAL_LOG, record)
        completed[key] = record
        results.append(record)
        if failure:
            print(f"    trial {number}/{N_ITER}: FAILED: {failure}", flush=True)
        else:
            print(
                f"    trial {number}/{N_ITER}: CV AP={mean_score:.4f} +/- {deviation:.4f} "
                f"({record['fit_seconds']:.1f}s)",
                flush=True,
            )
    if not any(row["status"] == "success" for row in results):
        raise RuntimeError(f"Every {algorithm} search trial failed for {hazard}")
    return results


def metric_bundle(y: np.ndarray, probabilities: np.ndarray, threshold: float = 0.5) -> dict[str, float | int]:
    predictions = probabilities >= threshold
    tn, fp, fn, tp = (int(value) for value in confusion_matrix(y, predictions, labels=[0, 1]).ravel())
    return {
        "threshold": threshold,
        "precision": float(precision_score(y, predictions, zero_division=0)),
        "recall": float(recall_score(y, predictions, zero_division=0)),
        "f1": float(f1_score(y, predictions, zero_division=0)),
        "pr_auc_average_precision": float(average_precision_score(y, probabilities)),
        "roc_auc": float(roc_auc_score(y, probabilities)),
        "brier_score": float(brier_score_loss(y, probabilities)),
        "true_negative": tn,
        "false_positive": fp,
        "false_negative": fn,
        "true_positive": tp,
        "false_alert_rate": float(fp / (fp + tn)) if fp + tn else 0.0,
    }


def threshold_rows(hazard: str, target: str, y: np.ndarray, probabilities: np.ndarray) -> list[dict[str, object]]:
    rows = []
    for threshold in THRESHOLDS:
        rows.append({"hazard": hazard, "target": target, **metric_bundle(y, probabilities, threshold)})
    return rows


def choose_threshold(rows: list[dict[str, object]]) -> dict[str, object]:
    return max(
        rows,
        key=lambda row: (
            float(row["f1"]),
            float(row["precision"]),
            float(row["recall"]),
            -float(row["false_alert_rate"]),
        ),
    )


def save_selected_artifact(
    hazard: str,
    target: str,
    algorithm: str,
    estimator,
    metadata: dict[str, object],
) -> tuple[Path, Path]:
    directory = MODEL_ROOT / hazard
    directory.mkdir(parents=True, exist_ok=True)
    model_path = directory / "model.joblib"
    metadata_path = directory / "metadata.json"
    if model_path.exists() or metadata_path.exists():
        raise FileExistsError(f"Refusing to overwrite existing selected model for {hazard}")
    temporary = model_path.with_name(f".{model_path.name}.tmp")
    joblib.dump(estimator, temporary, compress=3)
    temporary.replace(model_path)
    metadata.update({
        "model_path": model_path.relative_to(PROJECT_ROOT).as_posix(),
        "model_size_bytes": model_path.stat().st_size,
        "model_sha256": sha256(model_path),
        "metadata_path": metadata_path.relative_to(PROJECT_ROOT).as_posix(),
    })
    metadata_temp = metadata_path.with_name(f".{metadata_path.name}.tmp")
    metadata_temp.write_text(json.dumps(metadata, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    metadata_temp.replace(metadata_path)
    return model_path, metadata_path


def save_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(rows)
    temporary = path.with_name(f".{path.name}.tmp")
    frame.to_csv(temporary, index=False, encoding="utf-8")
    temporary.replace(path)


def select_models() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    if MODEL_ROOT.exists() and any(MODEL_ROOT.rglob("model.joblib")):
        raise FileExistsError(f"Selected Phase 7E model artifacts already exist under {MODEL_ROOT}")
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    PHASE_RESULTS.mkdir(parents=True, exist_ok=True)
    completed = load_trial_checkpoint()
    candidate_rows: list[dict[str, object]] = []
    selected_metadata: list[dict[str, object]] = []
    threshold_records: list[dict[str, object]] = []

    target_by_hazard = {hazard: target for target, hazard in HAZARDS.items()}
    for hazard, target in target_by_hazard.items():
        frame, features, data_hash = load_train_validation(target)
        train = frame[frame["split"].eq("train")]
        validation = frame[frame["split"].eq("validation")]
        X_train = train[features].to_numpy(dtype=np.float32)
        y_train = train[target].to_numpy(dtype=np.int8)
        X_validation = validation[features].to_numpy(dtype=np.float32)
        y_validation = validation[target].to_numpy(dtype=np.int8)
        train_dates = train["target_date"]
        candidate_objects = []

        print(
            f"\n{hazard}: temporal randomized search over {CANDIDATES[hazard]} "
            f"({N_ITER} trials x {N_SPLITS} expanding date folds each)",
            flush=True,
        )
        for algorithm in CANDIDATES[hazard]:
            results = run_trials(hazard, algorithm, X_train, y_train, train_dates, completed)
            successful = [row for row in results if row["status"] == "success"]
            best_trial = max(successful, key=lambda row: float(row["mean_average_precision"]))
            best_parameters = best_trial["parameters"]
            estimator = build_estimator(algorithm, best_parameters)
            started = time.perf_counter()
            with warnings.catch_warnings(record=True) as captured:
                warnings.simplefilter("always")
                estimator.fit(X_train, y_train)
            train_seconds = time.perf_counter() - started
            probabilities = positive_probabilities(estimator, X_validation)
            holdout_metrics = metric_bundle(y_validation, probabilities)
            base_row = {
                "hazard": hazard,
                "target": target,
                "algorithm": algorithm,
                "dataset_sha256": data_hash,
                "dataset_version": DATASET_VERSION,
                "label_scope": LABEL_SCOPE,
                "label_version": LABEL_VERSION,
                "cv_trial_count": len(results),
                "cv_success_count": len(successful),
                "best_cv_average_precision": float(best_trial["mean_average_precision"]),
                "best_cv_std_average_precision": float(best_trial["std_average_precision"]),
                "best_trial": int(best_trial["trial"]),
                "best_parameters": json.dumps(best_parameters, sort_keys=True, default=str),
                "validation_average_precision": holdout_metrics["pr_auc_average_precision"],
                "validation_roc_auc": holdout_metrics["roc_auc"],
                "validation_f1_at_0_5": holdout_metrics["f1"],
                "validation_false_alert_rate_at_0_5": holdout_metrics["false_alert_rate"],
                "validation_brier_at_0_5": holdout_metrics["brier_score"],
                "training_seconds": train_seconds,
                "warning_count": len(captured),
                "threshold": 0.5,
                "model_object": estimator,
                "validation_probabilities": probabilities,
            }
            candidate_objects.append(base_row)
            candidate_rows.append({key: value for key, value in base_row.items() if key not in {"model_object", "validation_probabilities"}})
            save_csv(CANDIDATE_METRICS_PATH, candidate_rows)
            print(
                f"  {algorithm}: best CV AP={base_row['best_cv_average_precision']:.4f}; "
                f"validation AP={base_row['validation_average_precision']:.4f}; "
                f"F1@0.5={base_row['validation_f1_at_0_5']:.4f}",
                flush=True,
            )

        selected = max(
            candidate_objects,
            key=lambda row: (
                float(row["validation_average_precision"]),
                float(row["best_cv_average_precision"]),
                -float(row["validation_false_alert_rate_at_0_5"]),
            ),
        )
        selected_algorithm = str(selected["algorithm"])
        probability_rows = threshold_rows(hazard, target, y_validation, selected["validation_probabilities"])
        threshold_records.extend(probability_rows)
        selected_threshold = choose_threshold(probability_rows)
        estimator = selected["model_object"]
        params = json.loads(str(selected["best_parameters"]))
        metadata = {
            "model_version": MODEL_VERSION,
            "hazard": hazard,
            "target": target,
            "label_type": "synthetic_development",
            "label_scope": LABEL_SCOPE,
            "label_version": LABEL_VERSION,
            "dataset_version": DATASET_VERSION,
            "dataset_sha256": data_hash,
            "feature_schema_version": VALIDATION_FEATURE_SCHEMA,
            "feature_columns": features,
            "feature_count": len(features),
            "selected_algorithm": selected_algorithm,
            "selection_reason": "Highest validation average precision among the two candidates selected from Phase 7D validation results; CV score and false-alert rate are tie-breakers.",
            "selected_parameters": params,
            "training_period": {
                "split": "train",
                "start": train["target_date"].min().strftime("%Y-%m-%d"),
                "end": train["target_date"].max().strftime("%Y-%m-%d"),
                "rows": len(train),
                "positive_rows": int(y_train.sum()),
            },
            "validation_period": {
                "split": "validation",
                "start": validation["target_date"].min().strftime("%Y-%m-%d"),
                "end": validation["target_date"].max().strftime("%Y-%m-%d"),
                "rows": len(validation),
                "positive_rows": int(y_validation.sum()),
            },
            "test_period": {
                "split": "test",
                "start": "2023-01-01",
                "end": "2025-10-31",
                "evaluation_status": "pending_final_evaluation",
            },
            "cross_validation": {
                "method": "20-trial randomized search with 3 expanding, non-overlapping date-block folds inside train",
                "best_mean_average_precision": float(selected["best_cv_average_precision"]),
                "best_fold_standard_deviation": float(selected["best_cv_std_average_precision"]),
                "trial_count_per_candidate": N_ITER,
            },
            "validation_metrics_at_0_5": {
                key: value for key, value in selected.items()
                if key.startswith("validation_") and key != "validation_probabilities"
            },
            "threshold_selection": {
                "method": "maximize validation F1 across 0.10..0.90; ties break by precision, recall, then lower false-alert rate",
                "selected_threshold": float(selected_threshold["threshold"]),
                "metrics": selected_threshold,
            },
            "calibration": {
                "method": "none",
                "calibrated": False,
                "reason": "The current synthetic validation positives are sparse for several hazards; retain raw estimator scores and report Brier score rather than fitting a calibrator on the same selection set.",
            },
            "baseline_selection": {
                "validation_average_precision": float(selected["validation_average_precision"]),
                "phase7d_validation_metrics": "results/ml/phase7d_baseline_validation_metrics.csv",
            },
            "random_seed": RANDOM_SEED,
            "software": {
                "python": sys.version.split()[0],
                "pandas": pd.__version__,
                "numpy": np.__version__,
                "scipy": scipy.__version__,
                "scikit_learn": sklearn.__version__,
                "joblib": joblib.__version__,
            },
            "test_metrics": None,
            "test_data_accessed": False,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        model_path, metadata_path = save_selected_artifact(hazard, target, selected_algorithm, estimator, metadata)
        metadata["model_sha256"] = sha256(model_path)
        selected_metadata.append(metadata)
        print(
            f"  selected {selected_algorithm}; threshold={selected_threshold['threshold']:.2f}; "
            f"validation F1={selected_threshold['f1']:.4f}",
            flush=True,
        )

        save_csv(THRESHOLD_PATH, threshold_records)
        atomic_metadata = metadata_path.with_name(f".{metadata_path.name}.tmp")
        atomic_metadata.write_text(json.dumps(metadata, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
        atomic_metadata.replace(metadata_path)
        del frame, X_train, X_validation, candidate_objects

    return candidate_rows, selected_metadata


def write_selection_report(candidate_rows: list[dict[str, object]], selected: list[dict[str, object]]) -> None:
    lines = [
        "# Phase 7E Model Selection (Validation Only)",
        "",
        "**SYNTHETIC_DEVELOPMENT_ONLY**",
        "",
        "## Method",
        "",
        "- Tuned the two strongest Phase 7D validation candidates per hazard; 20 deterministic randomized configurations per candidate.",
        "- Hyperparameters were scored with three expanding date-block folds inside the training period. All districts from a target date stayed in the same fold.",
        "- Final candidate comparison and threshold selection used the Phase 5 validation split only.",
        "- Threshold grid: 0.10 through 0.90 by 0.10; select maximum F1, ties by precision, recall, then lower false-alert rate.",
        "- Calibration: no post-hoc calibrator fitted; Brier score is reported for the uncalibrated estimator scores.",
        "- At selection close, the final test split remained unread; the separate one-time evaluation report documents the subsequent held-out evaluation.",
        "- These models reproduce synthetic weather-rule labels, not verified disaster events.",
        "",
        "## Candidate results",
        "",
        "| Hazard | Algorithm | CV AP (mean) | CV AP (SD) | Validation AP | Validation F1 at selected threshold | Selected threshold |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    selected_by_hazard = {item["hazard"]: item for item in selected}
    for row in sorted(candidate_rows, key=lambda item: (item["hazard"], item["algorithm"])):
        winner = selected_by_hazard[row["hazard"]]
        is_winner = row["algorithm"] == winner["selected_algorithm"]
        lines.append(
            f"| {row['hazard']} | {row['algorithm']}{' (selected)' if is_winner else ''} | "
            f"{float(row['best_cv_average_precision']):.4f} | "
            f"{float(row['best_cv_std_average_precision']):.4f} | "
            f"{float(row['validation_average_precision']):.4f} | "
            f"{float(winner['threshold_selection']['metrics']['f1']):.4f}{'*' if is_winner else ''} | "
            f"{float(winner['threshold_selection']['selected_threshold']):.2f}{'*' if is_winner else ''} |"
        )
    lines.extend(
        [
            "",
            "`*` denotes the selected model and its validation-tuned threshold for that hazard. Threshold F1 is shown only on the selected candidate row.",
            "",
            "## Selected model registry",
            "",
        ]
    )
    for item in selected:
        lines.append(
            f"- `{item['hazard']}`: `{item['selected_algorithm']}`, version `{item['model_version']}`, "
            f"threshold `{item['threshold_selection']['selected_threshold']:.2f}`, "
            f"validation AP `{item['validation_metrics_at_0_5']['validation_average_precision']:.4f}`."
        )
    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            "- Final selected development models and metadata: `models/development/phase7e_selected/`.",
            "- Candidate metrics: `results/ml/phase7e/candidate_validation_metrics.csv`.",
            "- Trial checkpoint log: `results/ml/phase7e/temporal_cv_trials.jsonl`.",
            "- Threshold analysis: `results/ml/phase7e/selected_threshold_analysis.csv`.",
            "- Test evaluation is a separate, one-time next step after this selection report.",
            "",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    print(f"Phase 7E tuning: {N_ITER} trials/candidate, {N_SPLITS} chronological folds", flush=True)
    candidate_rows, selected = select_models()
    write_selection_report(candidate_rows, selected)
    print(f"Selected development models: {MODEL_ROOT}", flush=True)
    print(f"Selection report: {REPORT_PATH}", flush=True)
    print("Final test split accessed: No", flush=True)
    return 0


def main_cli() -> int:
    try:
        return main()
    except (OSError, ValueError, KeyError, TypeError, AssertionError, RuntimeError) as exc:
        print(f"PHASE 7E TUNING FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main_cli())
