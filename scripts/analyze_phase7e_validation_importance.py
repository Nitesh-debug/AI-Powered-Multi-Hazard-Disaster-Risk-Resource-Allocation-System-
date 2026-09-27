"""Compute validation-only permutation importance for frozen synthetic models."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.train_phase7d_baselines import HAZARDS, LABEL_SCOPE, LABEL_VERSION, load_train_validation
from scripts.tune_phase7e_models import MODEL_ROOT, PHASE_RESULTS, sha256

OUTPUT_PATH = PHASE_RESULTS / "validation_permutation_importance.csv"
REPORT_PATH = PROJECT_ROOT / "results" / "ml" / "phase7e_validation_importance.md"
REPEATS = 3
SEED = 42


def analyze() -> list[dict[str, object]]:
    if OUTPUT_PATH.exists() or REPORT_PATH.exists():
        raise FileExistsError("Validation importance outputs already exist; refusing to overwrite")
    rows = []
    for target, hazard in HAZARDS.items():
        metadata_path = MODEL_ROOT / hazard / "metadata.json"
        model_path = MODEL_ROOT / hazard / "model.joblib"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata.get("label_scope") != LABEL_SCOPE or metadata.get("label_version") != LABEL_VERSION:
            raise ValueError(f"Synthetic scope metadata mismatch for {hazard}")
        if metadata.get("model_sha256") != sha256(model_path):
            raise ValueError(f"Selected model hash mismatch for {hazard}")
        frame, features, dataset_hash = load_train_validation(target)
        if dataset_hash != metadata.get("dataset_sha256") or metadata.get("feature_columns") != features:
            raise ValueError(f"Frozen dataset or feature contract mismatch for {hazard}")
        valid = frame.loc[frame["split"].eq("validation")]
        X = valid[features].to_numpy(dtype=np.float32)
        y = valid[target].to_numpy(dtype=np.int8)
        if len(X) != 7_300 or len(features) != 68:
            raise ValueError(f"Unexpected validation feature frame for {hazard}")
        estimator = joblib.load(model_path)
        baseline = float(metadata["validation_metrics_at_0_5"]["validation_average_precision"])
        result = permutation_importance(
            estimator,
            X,
            y,
            scoring="average_precision",
            n_repeats=REPEATS,
            random_state=SEED,
            n_jobs=2,
        )
        for feature, mean, deviation in zip(features, result.importances_mean, result.importances_std):
            rows.append({
                "hazard": hazard,
                "target": target,
                "feature": feature,
                "mean_average_precision_decrease": float(mean),
                "std_average_precision_decrease": float(deviation),
                "validation_average_precision": baseline,
                "permutation_repeats": REPEATS,
                "label_scope": LABEL_SCOPE,
                "label_version": LABEL_VERSION,
                "dataset_sha256": dataset_hash,
                "data_split_used": "validation_only",
                "test_data_accessed": False,
            })
        print(f"{hazard}: validation-only permutation importance complete", flush=True)
        del frame, X, y, estimator, result
    return rows


def main() -> int:
    rows = analyze()
    frame = pd.DataFrame(rows)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT_PATH.with_name(f".{OUTPUT_PATH.name}.tmp")
    frame.to_csv(temporary, index=False, encoding="utf-8")
    temporary.replace(OUTPUT_PATH)

    lines = [
        "# Phase 7E Validation-Only Feature Importance",
        "",
        "**SYNTHETIC_DEVELOPMENT_ONLY**",
        "",
        f"Permutation importance uses {REPEATS} repeats and average-precision decrease on the Phase 5 validation rows only. The final test split was not loaded.",
        "",
        "This describes which weather predictors help each selected model reproduce the Phase 7A rules. It is not causal attribution or evidence about real hazards.",
        "",
        "| Hazard | Top validation feature | Mean AP decrease | Validation AP |",
        "| --- | --- | ---: | ---: |",
    ]
    for hazard in HAZARDS.values():
        section = frame.loc[frame["hazard"].eq(hazard)].sort_values("mean_average_precision_decrease", ascending=False)
        top = section.iloc[0]
        lines.append(f"| {hazard} | `{top['feature']}` | {top['mean_average_precision_decrease']:.5f} | {top['validation_average_precision']:.4f} |")
    lines.extend(["", f"Full feature-level results: `{OUTPUT_PATH.relative_to(PROJECT_ROOT).as_posix()}`.", ""])
    temp_report = REPORT_PATH.with_name(f".{REPORT_PATH.name}.tmp")
    temp_report.write_text("\n".join(lines), encoding="utf-8")
    temp_report.replace(REPORT_PATH)
    if len(frame) != 6 * 68 or not frame["test_data_accessed"].eq(False).all():
        raise AssertionError("Validation-importance completeness check failed")
    print("PHASE 7E VALIDATION IMPORTANCE: PASS")
    print(f"Hazards: {len(HAZARDS)}; feature rows: {len(frame)}")
    print("Test split accessed: No")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError, AssertionError, FileExistsError) as exc:
        print(f"PHASE 7E VALIDATION IMPORTANCE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
