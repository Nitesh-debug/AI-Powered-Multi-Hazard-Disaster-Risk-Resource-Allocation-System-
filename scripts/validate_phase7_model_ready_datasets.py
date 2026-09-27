"""Validate Phase 7C model-ready synthetic development datasets."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd

import prepare_phase7_model_ready_datasets as preparation


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = PROJECT_ROOT / "results" / "phase7c_model_ready_dataset_validation.md"

FROZEN_HASHES = {
    preparation.WEATHER_PATH: "18eeac8a77735db0e408e0e5c685f3ac4c65eac3fd6d22f0bec6c805c4a65df0",
    preparation.LABEL_PATH: "c5efba704023f08753fa6dc5e9024b21f310852dfd153ae553b5d3301e941998",
    preparation.FEATURE_SCHEMA_PATH: "72f5d004d92144166f36771c1c98b0d2ce2e0b149952cef4a2e05eae8715ad05",
    preparation.SPLIT_PLAN_PATH: "10c5b8b321c2b698bb68531d9386efa5aae5317958715c00cd6e3730032c64ff",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_frozen_sources() -> None:
    for path, expected_hash in FROZEN_HASHES.items():
        if not path.exists():
            raise ValueError(f"Required frozen source is missing: {path.relative_to(PROJECT_ROOT)}")
        if sha256(path) != expected_hash:
            raise ValueError(f"Frozen source changed: {path.relative_to(PROJECT_ROOT)}")


def load_actual(path: Path, target: str) -> pd.DataFrame:
    if not path.exists():
        raise ValueError(f"Model-ready dataset is missing: {path.relative_to(PROJECT_ROOT)}")
    return pd.read_csv(
        path,
        parse_dates=["feature_reference_date", "target_date"],
        dtype={target: "int8"},
        compression="gzip",
        low_memory=False,
    )


def validate_dataset(
    actual: pd.DataFrame,
    expected: pd.DataFrame,
    feature_columns: list[str],
    target: str,
) -> None:
    expected_columns = [
        "district",
        "feature_reference_date",
        "target_date",
        "split",
        "synthetic_label_scope",
        "synthetic_rule_version",
        *feature_columns,
        target,
    ]
    if actual.columns.tolist() != expected_columns:
        raise ValueError(f"{target} has an invalid column contract")
    if actual.duplicated(["district", "target_date"]).any():
        raise ValueError(f"{target} contains duplicate district-target-date rows")
    if actual[feature_columns].isna().any().any():
        raise ValueError(f"{target} contains missing predictor values")
    if not set(actual[target].unique()) <= {0, 1}:
        raise ValueError(f"{target} contains values other than 0 and 1")
    if not actual["synthetic_label_scope"].eq(preparation.SYNTHETIC_LABEL_SCOPE).all():
        raise ValueError(f"{target} has invalid synthetic scope metadata")
    if not actual["synthetic_rule_version"].eq(preparation.RULE_VERSION).all():
        raise ValueError(f"{target} has invalid rule-version metadata")
    if not actual["feature_reference_date"].eq(actual["target_date"] - pd.Timedelta(days=1)).all():
        raise ValueError(f"{target} violates one-day-ahead target alignment")

    other_labels = set(preparation.LABEL_COLUMNS) - {target}
    if other_labels.intersection(actual.columns):
        raise ValueError(f"{target} contains another hazard label")
    forbidden_verified_fields = {
        "flood_event_label",
        "label_status",
        "label_source",
        "label_source_url",
        "flood_event_ids",
        "synthetic_unavailable_reason",
    }
    if forbidden_verified_fields.intersection(feature_columns):
        raise ValueError(f"{target} predictor list contains label or provenance fields")

    sorted_keys = actual[["target_date", "district"]].sort_values(
        ["target_date", "district"], kind="stable", ignore_index=True
    )
    pd.testing.assert_frame_equal(
        actual[["target_date", "district"]].reset_index(drop=True),
        sorted_keys,
        check_dtype=False,
    )

    split_bounds = {
        "train": (pd.Timestamp("2020-01-02"), pd.Timestamp("2021-12-31")),
        "validation": (pd.Timestamp("2022-01-01"), pd.Timestamp("2022-12-31")),
        "test": (pd.Timestamp("2023-01-01"), pd.Timestamp("2025-10-31")),
    }
    for split, (start, end) in split_bounds.items():
        subset = actual[actual["split"].eq(split)]
        if subset.empty or not subset["target_date"].between(start, end).all():
            raise ValueError(f"{target} has invalid or empty {split} coverage")
        if subset["district"].nunique() != preparation.EXPECTED_DISTRICTS:
            raise ValueError(f"{target} has incomplete district coverage in {split}")
    if not (
        actual.loc[actual["split"].eq("train"), "target_date"].max()
        < actual.loc[actual["split"].eq("validation"), "target_date"].min()
        < actual.loc[actual["split"].eq("test"), "target_date"].min()
    ):
        raise ValueError(f"{target} temporal splits are not chronological")

    pd.testing.assert_frame_equal(
        actual.reset_index(drop=True),
        expected.reset_index(drop=True),
        check_dtype=False,
        check_exact=False,
        rtol=1e-12,
        atol=1e-12,
    )


def build_report(
    summaries: list[dict[str, object]],
    feature_columns: list[str],
    output_hashes: dict[str, str],
) -> str:
    lines = [
        "# Phase 7C Model-Ready Synthetic Dataset Validation",
        "",
        "## Result",
        "",
        "**PASS**",
        "",
        "Six hazard-specific supervised-development datasets were created. They contain synthetic development targets only; no verified disaster labels were changed or combined with them, and no ML model was trained.",
        "",
        "## Dataset summary",
        "",
        "| Target | Rows | Positive | Negative | Source `UNAVAILABLE` | Total excluded | Districts | Target dates | Features | Train | Validation | Test |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: |",
    ]
    for item in summaries:
        split = item["split_counts"]
        lines.append(
            f"| `{item['target']}` | {item['rows']:,} | {item['positive']:,} | "
            f"{item['negative']:,} | {item['source_unavailable']:,} | "
            f"{item['excluded_total']:,} | {item['districts']} | "
            f"`{item['target_start']:%Y-%m-%d}` to `{item['target_end']:%Y-%m-%d}` | "
            f"{item['feature_count']} | {split['train']:,} | {split['validation']:,} | {split['test']:,} |"
        )
    lines.extend(
        [
            "",
            "`Total excluded` is the source-label row count minus final model-ready rows. It includes out-of-split dates, `UNAVAILABLE` targets, and rows lacking a complete prior-day predictor vector; categories may overlap.",
            "",
            "## Split class counts",
            "",
            "| Target | Split | Rows | Positive | Negative |",
            "| --- | --- | ---: | ---: | ---: |",
        ]
    )
    for item in summaries:
        for split in ["train", "validation", "test"]:
            rows = item["split_counts"][split]
            positive = item["split_positive"][split]
            lines.append(
                f"| `{item['target']}` | {split} | {rows:,} | {positive:,} | {rows - positive:,} |"
            )
    lines.extend(
        [
            "",
            "## Validation checks",
            "",
            f"- Predictor contract: {len(feature_columns)} Phase 5 weather features in every dataset.",
            "- One-day alignment: `feature_reference_date = target_date - 1 day` on every row.",
            "- Leakage: predictor values were independently reconstructed from `feature_reference_date`; no target-date weather, verified-label field, provenance field, or other hazard target is present.",
            "- Label usability: each target contains only integer `0` or `1`; all `UNAVAILABLE` rows are excluded without conversion.",
            "- Metadata: every row preserves `SYNTHETIC_DEVELOPMENT_ONLY` and `phase7a_v1`.",
            "- Splits: Phase 5 train, validation, and test boundaries are chronological and non-overlapping; district-days were not randomly split.",
            "- Coverage: all 20 districts occur in every hazard and every split.",
            "- Inputs: frozen weather, synthetic-label, feature-schema, and split-plan hashes are unchanged.",
            "- ML models trained: No.",
            "",
            "## Artifacts",
            "",
        ]
    )
    for target in preparation.LABEL_COLUMNS:
        path = preparation.OUTPUT_PATHS[target].relative_to(PROJECT_ROOT).as_posix()
        lines.append(f"- `{path}` SHA-256: `{output_hashes[target]}`")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    verify_frozen_sources()
    expected_outputs, summaries, feature_columns = preparation.build_model_ready_frames()
    output_hashes = {}
    for target in preparation.LABEL_COLUMNS:
        path = preparation.OUTPUT_PATHS[target]
        actual = load_actual(path, target)
        validate_dataset(actual, expected_outputs[target], feature_columns, target)
        output_hashes[target] = sha256(path)
    verify_frozen_sources()

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        build_report(summaries, feature_columns, output_hashes), encoding="utf-8"
    )

    print("=" * 72)
    print("PHASE 7C MODEL-READY DATASET VALIDATION")
    print("=" * 72)
    for item in summaries:
        print(
            f"{item['target']}: rows={item['rows']:,}, positives={item['positive']:,}, "
            f"negatives={item['negative']:,}, excluded={item['excluded_total']:,}"
        )
    print("No target-date leakage: PASS")
    print("No label columns in predictors: PASS")
    print("Chronological split ordering: PASS")
    print("District coverage: PASS")
    print("Synthetic metadata: PASS")
    print("Frozen input hashes: PASS")
    print("Expected target alignment: PASS")
    print("ML models trained: No")
    print(f"Report: {REPORT_PATH}")
    print("Result: PASS")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, TypeError, AssertionError) as exc:
        print(f"PHASE 7C VALIDATION FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
