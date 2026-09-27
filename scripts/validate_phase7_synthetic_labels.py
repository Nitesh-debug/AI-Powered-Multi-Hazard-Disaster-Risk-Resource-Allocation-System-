"""Validate the Phase 7 synthetic development-label artifact."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd

import generate_phase7_synthetic_labels as generator


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = PROJECT_ROOT / "data" / "development" / "phase7_synthetic_development_labels.csv"
REPORT_PATH = PROJECT_ROOT / "results" / "phase7b_synthetic_label_validation.md"

FROZEN_HASHES = {
    "data/processed/weather_features.csv": "18eeac8a77735db0e408e0e5c685f3ac4c65eac3fd6d22f0bec6c805c4a65df0",
    "data/processed/daily_flood_dataset.csv": "609154b4f62a4628f464decbb668722d230386580b69f872db53cc6704d172a2",
    "data/raw/disasters/curated_flood_events.csv": "def5bfb0dc24c6c02f69926cd29e7ca3a73ee5edecb766e6c7627cf460cc9779",
}

FORBIDDEN_OUTPUT_COLUMNS = {
    *generator.RULE_FEATURES,
    "flood_event_label",
    "label_status",
    "label_source",
    "label_source_url",
    "flood_event_ids",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def label_counts(frame: pd.DataFrame) -> list[dict[str, object]]:
    rows = []
    for label in generator.LABEL_COLUMNS:
        counts = frame[label].value_counts(dropna=False)
        rows.append(
            {
                "label": label,
                "positive": int(counts.get("1", 0)),
                "zero": int(counts.get("0", 0)),
                "unavailable": int(counts.get("UNAVAILABLE", 0)),
            }
        )
    return rows


def build_report(frame: pd.DataFrame, counts: list[dict[str, object]], output_hash: str) -> str:
    lines = [
        "# Phase 7B Synthetic Development-Label Validation",
        "",
        "## Result",
        "",
        "**PASS**",
        "",
        "This artifact contains synthetic development targets only. It does not contain verified historical disaster labels and no ML model was trained.",
        "",
        "## Artifact",
        "",
        f"- Dataset: `data/development/{OUTPUT_PATH.name}`",
        f"- Rows: {len(frame):,}",
        f"- Districts: {frame['district'].nunique()}",
        f"- Target dates: `{frame['target_date'].min().date()}` to `{frame['target_date'].max().date()}`",
        f"- Scope: `{generator.SYNTHETIC_LABEL_SCOPE}` on every row",
        f"- Rule version: `{generator.RULE_VERSION}` on every row",
        f"- SHA-256: `{output_hash}`",
        "",
        "## Label counts",
        "",
        "| Synthetic development label | Positive (`1`) | Zero (`0`) | `UNAVAILABLE` |",
        "| --- | ---: | ---: | ---: |",
    ]
    for item in counts:
        lines.append(
            f"| `{item['label']}` | {item['positive']:,} | {item['zero']:,} | {item['unavailable']:,} |"
        )
    lines.extend(
        [
            "",
            "## Safeguards",
            "",
            "- Processed weather, verified flood labels, and curated flood-event hashes are unchanged.",
            f"- Threshold calibration is restricted to `{generator.TRAINING_START.date()}` through `{generator.TRAINING_END.date()}`.",
            "- The output contains no target-date weather feature columns.",
            "- `feature_reference_date` is exactly one day before `target_date` on every row.",
            "- Later one-day-ahead model-ready data must join predictors using `district` and `feature_reference_date`, never target-date weather.",
            "- Missing rule inputs remain `UNAVAILABLE`; they are not converted to zero.",
            "- Synthetic labels remain separate from verified disaster labels.",
            "- ML models trained: No.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    if not OUTPUT_PATH.exists():
        raise ValueError(f"Synthetic development dataset is missing: {OUTPUT_PATH.relative_to(PROJECT_ROOT)}")

    for relative_path, expected_hash in FROZEN_HASHES.items():
        path = PROJECT_ROOT / relative_path
        if not path.exists():
            raise ValueError(f"Frozen source is missing: {relative_path}")
        if sha256(path) != expected_hash:
            raise ValueError(f"Frozen source changed: {relative_path}")

    frame = pd.read_csv(
        OUTPUT_PATH,
        dtype={label: "string" for label in generator.LABEL_COLUMNS},
        parse_dates=["target_date", "feature_reference_date"],
        keep_default_na=False,
    )
    if list(frame.columns) != generator.OUTPUT_COLUMNS:
        raise ValueError("Synthetic output columns do not match the Phase 7A contract")
    if len(frame) != generator.EXPECTED_DAILY_ROWS:
        raise ValueError(f"Synthetic row count is {len(frame):,}; expected {generator.EXPECTED_DAILY_ROWS:,}")
    if frame["district"].nunique() != generator.EXPECTED_DISTRICTS:
        raise ValueError(
            f"Synthetic district count is {frame['district'].nunique()}; expected {generator.EXPECTED_DISTRICTS}"
        )
    if frame.duplicated(["district", "target_date"]).any():
        raise ValueError("Synthetic output contains duplicate district-date rows")
    if not frame["synthetic_label_scope"].eq(generator.SYNTHETIC_LABEL_SCOPE).all():
        raise ValueError("Every output row must carry SYNTHETIC_DEVELOPMENT_ONLY")
    if not frame["synthetic_rule_version"].eq(generator.RULE_VERSION).all():
        raise ValueError("Every output row must carry rule version phase7a_v1")
    if not frame["feature_reference_date"].eq(frame["target_date"] - pd.Timedelta(days=1)).all():
        raise ValueError("feature_reference_date must be exactly one day before target_date")
    if FORBIDDEN_OUTPUT_COLUMNS.intersection(frame.columns):
        raise ValueError("Synthetic label artifact contains weather or verified-label columns")

    allowed_values = {"1", "0", "UNAVAILABLE"}
    for label in generator.LABEL_COLUMNS:
        values = set(frame[label].unique())
        if not values <= allowed_values:
            raise ValueError(f"{label} contains invalid values: {sorted(values - allowed_values)}")
        unavailable = frame[label].eq("UNAVAILABLE")
        if unavailable.any() and frame.loc[unavailable, "synthetic_unavailable_reason"].eq("").any():
            raise ValueError(f"{label} has UNAVAILABLE rows without an explicit reason")

    weather = generator.load_weather()
    expected = generator.generate_synthetic_labels(weather).copy()
    for column in ("target_date", "feature_reference_date"):
        expected[column] = pd.to_datetime(expected[column])
    pd.testing.assert_frame_equal(
        frame.reset_index(drop=True),
        expected.reset_index(drop=True),
        check_dtype=False,
        check_like=False,
    )

    counts = label_counts(frame)
    for item in counts:
        if item["positive"] + item["zero"] + item["unavailable"] != len(frame):
            raise ValueError(f"Label counts do not reconcile for {item['label']}")

    output_hash = sha256(OUTPUT_PATH)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(build_report(frame, counts, output_hash), encoding="utf-8")

    print("=" * 72)
    print("PHASE 7B SYNTHETIC DEVELOPMENT-LABEL VALIDATION")
    print("=" * 72)
    print(f"Rows: {len(frame):,}")
    print(f"Districts: {frame['district'].nunique()}")
    for item in counts:
        print(
            f"{item['label']}: positives={item['positive']:,}, "
            f"zeros={item['zero']:,}, unavailable={item['unavailable']:,}"
        )
    print("Frozen raw/processed hashes: PASS")
    print("Scope and rule version: PASS")
    print("One-day-ahead leakage checks: PASS")
    print("Recomputed rule equality: PASS")
    print("ML models trained: No")
    print(f"Report: {REPORT_PATH}")
    print("Result: PASS")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, TypeError, AssertionError) as exc:
        print(f"PHASE 7B VALIDATION FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
