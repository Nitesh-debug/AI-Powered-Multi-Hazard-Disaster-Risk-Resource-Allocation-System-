from pathlib import Path
import json
import time

import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_ROOT / "data" / "development" / "model_ready"
OUTPUT_DIR = PROJECT_ROOT / "results" / "phase7d_xgb_lgbm"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


HAZARDS = {
    "coldwave": {
        "file": "phase7c_synthetic_coldwave_dev_v1.csv.gz",
        "target": "synthetic_coldwave_dev_v1",
    },
    "flood": {
        "file": "phase7c_synthetic_flood_dev_v1.csv.gz",
        "target": "synthetic_flood_dev_v1",
    },
    "heavy_rain": {
        "file": "phase7c_synthetic_heavy_rain_dev_v1.csv.gz",
        "target": "synthetic_heavy_rain_dev_v1",
    },
    "landslide": {
        "file": "phase7c_synthetic_landslide_dev_v1.csv.gz",
        "target": "synthetic_landslide_dev_v1",
    },
    "heatwave": {
        "file": "phase7c_synthetic_heatwave_dev_v1.csv.gz",
        "target": "synthetic_heatwave_dev_v1",
    },
    "windstorm": {
        "file": "phase7c_synthetic_windstorm_dev_v1.csv.gz",
        "target": "synthetic_windstorm_dev_v1",
    },
}


def get_feature_columns(df, target_col):
    """
    Keep only the 68 numeric weather predictors.

    Metadata and target columns are excluded.
    """

    excluded = {
        "district",
        "feature_reference_date",
        "target_date",
        "split",
        "synthetic_label_scope",
        "synthetic_rule_version",
        target_col,
    }

    feature_cols = [
        col
        for col in df.columns
        if col not in excluded
        and pd.api.types.is_numeric_dtype(df[col])
    ]

    if len(feature_cols) != 68:
        raise ValueError(
            f"Expected 68 numeric predictors, found {len(feature_cols)}"
        )

    return feature_cols


def train_xgboost(X_train, y_train):
    model = XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=-1,
        eval_metric="logloss",
        tree_method="hist",
        verbosity=0,
    )

    model.fit(X_train, y_train)

    return model


def train_lightgbm(X_train, y_train):
    model = LGBMClassifier(
        n_estimators=300,
        learning_rate=0.05,
        num_leaves=31,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=-1,
        verbosity=-1,
    )

    model.fit(X_train, y_train)

    return model


def evaluate(model, X, y):
    scores = model.predict_proba(X)[:, 1]

    return {
        "average_precision": float(
            average_precision_score(y, scores)
        ),
        "roc_auc": float(
            roc_auc_score(y, scores)
        ),
    }


def main():

    all_results = []

    print("=" * 80)
    print("PHASE 7D — XGBOOST + LIGHTGBM BASELINE EXPERIMENT")
    print("=" * 80)
    print()
    print("IMPORTANT:")
    print("- Existing Phase 7D/7E artifacts will NOT be modified.")
    print("- Test split will NOT be read.")
    print("- Synthetic labels are DEVELOPMENT ONLY.")
    print()

    for hazard, config in HAZARDS.items():

        filename = config["file"]
        target_col = config["target"]

        path = DATA_DIR / filename

        print()
        print("=" * 80)
        print(f"HAZARD: {hazard}")
        print(f"FILE:   {filename}")
        print(f"TARGET: {target_col}")
        print("=" * 80)

        start = time.time()

        df = pd.read_csv(
            path,
            compression="gzip",
        )

        print(f"Rows:    {len(df):,}")
        print(f"Columns: {len(df.columns):,}")

        if target_col not in df.columns:
            raise ValueError(
                f"Target column '{target_col}' not found."
            )

        if "split" not in df.columns:
            raise ValueError(
                "Required 'split' column not found."
            )

        feature_cols = get_feature_columns(
            df,
            target_col,
        )

        print(f"Features: {len(feature_cols)}")

        train_df = df[
            df["split"].astype(str).str.lower() == "train"
        ].copy()

        validation_df = df[
            df["split"].astype(str).str.lower().isin(
                ["validation", "val"]
            )
        ].copy()

        if len(train_df) == 0:
            raise ValueError(
                f"No training rows found for {hazard}"
            )

        if len(validation_df) == 0:
            raise ValueError(
                f"No validation rows found for {hazard}"
            )

        X_train = train_df[feature_cols]
        y_train = train_df[target_col].astype(int)

        X_validation = validation_df[feature_cols]
        y_validation = validation_df[target_col].astype(int)

        print(f"Train rows:       {len(train_df):,}")
        print(f"Validation rows:  {len(validation_df):,}")
        print(f"Train positives:  {y_train.sum():,}")
        print(f"Validation pos.:  {y_validation.sum():,}")

        models = {
            "xgboost": train_xgboost,
            "lightgbm": train_lightgbm,
        }

        for algorithm, trainer in models.items():

            print()
            print(f"Training {algorithm}...")

            model_start = time.time()

            model = trainer(
                X_train,
                y_train,
            )

            metrics = evaluate(
                model,
                X_validation,
                y_validation,
            )

            elapsed = time.time() - model_start

            result = {
                "experiment": "phase7d_xgb_lgbm_v1",
                "hazard": hazard,
                "algorithm": algorithm,
                "train_rows": len(train_df),
                "validation_rows": len(validation_df),
                "n_features": len(feature_cols),
                "train_positive_count": int(y_train.sum()),
                "validation_positive_count": int(
                    y_validation.sum()
                ),
                "average_precision": metrics[
                    "average_precision"
                ],
                "roc_auc": metrics["roc_auc"],
                "fit_seconds": elapsed,
                "random_state": 42,
            }

            all_results.append(result)

            print(
                f"PR-AUC:  {metrics['average_precision']:.6f}"
            )

            print(
                f"ROC-AUC: {metrics['roc_auc']:.6f}"
            )

            print(
                f"Time:    {elapsed:.1f} seconds"
            )

        print(
            f"Completed {hazard} "
            f"in {time.time() - start:.1f} seconds"
        )

    results_df = pd.DataFrame(all_results)

    results_df = results_df.sort_values(
        ["hazard", "average_precision"],
        ascending=[True, False],
    )

    output_csv = (
        OUTPUT_DIR /
        "phase7d_xgb_lgbm_validation.csv"
    )

    results_df.to_csv(
        output_csv,
        index=False,
    )

    metadata = {
        "experiment": "phase7d_xgb_lgbm_v1",
        "algorithms": [
            "XGBoost",
            "LightGBM",
        ],
        "hazards": list(HAZARDS.keys()),
        "feature_count": 68,
        "test_split_used": False,
        "synthetic_labels": True,
        "existing_phase7d_7e_artifacts_modified": False,
        "warning": (
            "Metrics evaluate synthetic development labels "
            "and do not establish real-world disaster "
            "prediction skill."
        ),
    }

    with open(
        OUTPUT_DIR / "metadata.json",
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            metadata,
            f,
            indent=2,
        )

    print()
    print("=" * 80)
    print("EXPERIMENT COMPLETE")
    print("=" * 80)

    print(
        results_df.to_string(index=False)
    )

    print()
    print("Results saved to:")
    print(output_csv)


if __name__ == "__main__":
    main()