"""Design the Phase 5 ML dataset without materializing training data."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DAILY_FLOOD_PATH = PROJECT_ROOT / "data" / "processed" / "daily_flood_dataset.csv"
ASSESSMENT_PATH = PROJECT_ROOT / "results" / "phase4_disaster_data_assessment.csv"
DESIGN_MD_PATH = PROJECT_ROOT / "results" / "phase5_ml_dataset_design.md"
FEATURE_SCHEMA_PATH = PROJECT_ROOT / "results" / "phase5_ml_feature_schema.csv"
SPLIT_PLAN_PATH = PROJECT_ROOT / "results" / "phase5_temporal_split_plan.csv"
SUMMARY_PATH = PROJECT_ROOT / "results" / "phase5_ml_dataset_summary.csv"

LEAD_DAYS = 1
EXPECTED_DISTRICTS = 20
EXPECTED_TOTAL_DISTRICT_DAYS = 42_620
EXPECTED_VERIFIED_FLOOD_POSITIVES = 32

TEMPORAL_SPLITS = [
    ("train", "2020-01-02", "2021-12-31"),
    ("validation", "2022-01-01", "2022-12-31"),
    ("test", "2023-01-01", "2025-10-31"),
]

TARGET_COLUMNS = {"flood_event_label", "label_status"}
PROVENANCE_COLUMNS = {"label_source", "label_source_url", "flood_event_ids"}
KEY_COLUMNS = {"district", "date"}
STATIC_CONTEXT_COLUMNS = {"latitude", "longitude"}
BASE_DAILY_COLUMNS = {
    "precipitation_daily_sum",
    "rain_daily_sum",
    "snowfall_daily_sum",
    "temperature_2m_daily_mean",
    "temperature_2m_daily_min",
    "temperature_2m_daily_max",
    "relative_humidity_2m_daily_mean",
    "relative_humidity_2m_daily_max",
    "wind_speed_10m_daily_mean",
    "wind_speed_10m_daily_max",
    "wind_gusts_10m_daily_max",
    "soil_moisture_0_to_7cm_daily_mean",
    "soil_moisture_7_to_28cm_daily_mean",
    "soil_moisture_28_to_100cm_daily_mean",
    "soil_temperature_0_to_7cm_daily_mean",
    "soil_temperature_7_to_28cm_daily_mean",
    "soil_temperature_28_to_100cm_daily_mean",
    "snow_depth_end_of_day",
    "weather_code_mode",
}


def classify_column(column: str) -> tuple[str, str, str]:
    if column in KEY_COLUMNS:
        return (
            "key",
            "carry",
            "Used to join source rows and define target dates; not an input feature.",
        )
    if column in TARGET_COLUMNS:
        return (
            "target",
            "exclude_from_features",
            "Target/status fields must never be used as model inputs.",
        )
    if column in PROVENANCE_COLUMNS:
        return (
            "label_provenance",
            "exclude_from_features",
            "Source provenance is for audit only and would leak the label.",
        )
    if column in STATIC_CONTEXT_COLUMNS:
        return (
            "static_context",
            "optional_context_after_review",
            "Static geography may help spatial risk scoring, but sparse labels can make it memorize districts.",
        )
    if column in BASE_DAILY_COLUMNS:
        return (
            "daily_weather_feature",
            f"shift_by_{LEAD_DAYS}_day",
            "Use from feature_reference_date only; never same target date for forecasting.",
        )
    return (
        "engineered_weather_feature",
        f"shift_by_{LEAD_DAYS}_day",
        "Past-looking lag/rolling feature from feature_reference_date; validate warm-up missingness.",
    )


def validate_source_frame(frame: pd.DataFrame) -> None:
    if len(frame) != EXPECTED_TOTAL_DISTRICT_DAYS:
        raise ValueError(f"Daily flood row count is {len(frame):,}; expected {EXPECTED_TOTAL_DISTRICT_DAYS:,}")
    if frame["district"].nunique() != EXPECTED_DISTRICTS:
        raise ValueError(f"District count is {frame['district'].nunique()}; expected {EXPECTED_DISTRICTS}")
    if frame["date"].isna().any():
        raise ValueError("Daily flood dataset contains invalid dates")
    if frame.duplicated(["district", "date"]).any():
        raise ValueError("Daily flood dataset contains duplicate district-date rows")
    positive_count = int(frame["label_status"].eq("VERIFIED_FLOOD").sum())
    if positive_count != EXPECTED_VERIFIED_FLOOD_POSITIVES:
        raise ValueError(f"Verified flood positives are {positive_count}; expected {EXPECTED_VERIFIED_FLOOD_POSITIVES}")
    if frame.loc[frame["label_status"].eq("NO_VERIFIED_EVENT"), "flood_event_label"].notna().any():
        raise ValueError("Unknown/no-verified-event rows must not carry binary negative labels")


def build_feature_schema(columns: list[str]) -> pd.DataFrame:
    rows = []
    for column in columns:
        role, action, leakage_note = classify_column(column)
        rows.append(
            {
                "source_column": column,
                "role": role,
                "phase6_baseline_action": action,
                "leakage_note": leakage_note,
            }
        )
    return pd.DataFrame(rows)


def assert_lead_day_available(frame: pd.DataFrame) -> None:
    available = frame[["district", "date"]].rename(columns={"date": "feature_reference_date"})
    target = frame[["district", "date"]].copy()
    target["feature_reference_date"] = target["date"] - pd.Timedelta(days=LEAD_DAYS)
    target = target[target["feature_reference_date"] >= frame["date"].min()]
    merged = target.merge(available, on=["district", "feature_reference_date"], how="left", indicator=True)
    if not merged["_merge"].eq("both").all():
        raise ValueError("At least one target row lacks a prior-day feature row")


def build_split_plan(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    previous_end: pd.Timestamp | None = None
    for split_name, start_text, end_text in TEMPORAL_SPLITS:
        start = pd.Timestamp(start_text)
        end = pd.Timestamp(end_text)
        if previous_end is not None and start != previous_end + pd.Timedelta(days=1):
            raise ValueError("Temporal splits must be contiguous")
        previous_end = end

        subset = frame[(frame["date"] >= start) & (frame["date"] <= end)]
        rows.append(
            {
                "split": split_name,
                "feature_reference_start_date": (start - pd.Timedelta(days=LEAD_DAYS)).strftime("%Y-%m-%d"),
                "feature_reference_end_date": (end - pd.Timedelta(days=LEAD_DAYS)).strftime("%Y-%m-%d"),
                "target_start_date": start.strftime("%Y-%m-%d"),
                "target_end_date": end.strftime("%Y-%m-%d"),
                "district_days": len(subset),
                "district_count": subset["district"].nunique(),
                "verified_flood_positives": int(subset["label_status"].eq("VERIFIED_FLOOD").sum()),
                "unknown_no_verified_event_days": int(subset["label_status"].eq("NO_VERIFIED_EVENT").sum()),
                "confirmed_negative_days": 0,
                "supervised_binary_ready": "No",
            }
        )
    split_plan = pd.DataFrame(rows)
    eligible_rows = len(frame[frame["date"] >= pd.Timestamp(TEMPORAL_SPLITS[0][1])])
    if int(split_plan["district_days"].sum()) != eligible_rows:
        raise ValueError("Split rows do not cover all one-day-lead eligible target rows")
    return split_plan


def build_summary(frame: pd.DataFrame, split_plan: pd.DataFrame) -> pd.DataFrame:
    assessment = pd.read_csv(ASSESSMENT_PATH, dtype=str)
    flood_status = assessment.loc[assessment["disaster"].eq("Flood"), "label_status"].iloc[0]
    return pd.DataFrame(
        [
            ("phase", "Phase 5: ML dataset design"),
            ("source_dataset", "data/processed/daily_flood_dataset.csv"),
            ("source_dataset_rows", str(len(frame))),
            ("source_dataset_columns", str(len(frame.columns))),
            ("district_count", str(frame["district"].nunique())),
            ("date_start", frame["date"].min().strftime("%Y-%m-%d")),
            ("date_end", frame["date"].max().strftime("%Y-%m-%d")),
            ("prediction_lead_days", str(LEAD_DAYS)),
            ("lead_eligible_district_days", str(int(split_plan["district_days"].sum()))),
            ("verified_flood_positives", str(int(frame["label_status"].eq("VERIFIED_FLOOD").sum()))),
            ("unknown_no_verified_event_days", str(int(frame["label_status"].eq("NO_VERIFIED_EVENT").sum()))),
            ("confirmed_negative_days", "0"),
            ("flood_phase4_label_status", flood_status),
            ("supervised_binary_training_ready", "No"),
            ("synthetic_labels_created", "No"),
            ("processed_data_modified", "No"),
            ("ml_models_trained", "No"),
        ],
        columns=["metric", "value"],
    )


def write_design_report(frame: pd.DataFrame, feature_schema: pd.DataFrame, split_plan: pd.DataFrame) -> None:
    included_count = int(feature_schema["phase6_baseline_action"].str.startswith("shift_by_").sum())
    positive_count = int(frame["label_status"].eq("VERIFIED_FLOOD").sum())
    unknown_count = int(frame["label_status"].eq("NO_VERIFIED_EVENT").sum())
    split_lines = [
        f"- `{row.split}`: target `{row.target_start_date}` to `{row.target_end_date}`, "
        f"{row.district_days:,} district-days, {row.verified_flood_positives} verified positives, "
        f"{row.unknown_no_verified_event_days:,} unknown days, 0 confirmed negatives."
        for row in split_plan.itertuples(index=False)
    ]
    excluded = feature_schema[feature_schema["phase6_baseline_action"].eq("exclude_from_features")]["source_column"].tolist()

    lines = [
        "# Phase 5 ML Dataset Design",
        "",
        "## Decision",
        "Phase 5 defines a leakage-aware ML dataset contract but does not materialize a new processed dataset and does not train a model.",
        "",
        "The forecast contract is a one-day lead design: features from `feature_reference_date` may be used to predict a target label for `target_date = feature_reference_date + 1 day`. Same-day daily weather can be used only for event-day analysis, not for a forecasting baseline.",
        "",
        "## Source and unit",
        "- Source table: `data/processed/daily_flood_dataset.csv`.",
        "- Unit of analysis: one district and one target date.",
        f"- Source coverage: {frame['district'].nunique()} districts, `{frame['date'].min():%Y-%m-%d}` to `{frame['date'].max():%Y-%m-%d}`.",
        f"- Source rows: {len(frame):,}; one-day-lead eligible target rows: {int(split_plan['district_days'].sum()):,}.",
        "",
        "## Label semantics",
        f"- `VERIFIED_FLOOD`: {positive_count} district-days with documented flood provenance.",
        f"- `NO_VERIFIED_EVENT`: {unknown_count:,} district-days whose flood status is unknown/not established.",
        "- Confirmed negative flood labels: 0.",
        "- `NO_VERIFIED_EVENT` must not be converted to `0` for supervised binary training.",
        "- No synthetic labels are introduced by this phase.",
        "",
        "## Feature contract",
        f"- Baseline shifted weather inputs: {included_count} columns, listed in `phase5_ml_feature_schema.csv`.",
        "- `district` and `date` are keys, not model inputs.",
        "- `latitude` and `longitude` are optional context after review because sparse labels can make static geography act like district memorization.",
        f"- Excluded audit/target columns: {', '.join(f'`{column}`' for column in excluded)}.",
        "- Any calendar features in Phase 6 must be derived from `feature_reference_date`, not from future target context beyond the requested lead time.",
        "",
        "## Temporal split plan",
        *split_lines,
        "",
        "These splits are chronological and non-overlapping. They are suitable for design validation and future backtesting discipline, but they do not make the current data supervised-binary-ready because the non-positive rows are unknown rather than confirmed negative.",
        "",
        "## Phase 6 gate",
        "Before disaster prediction starts, the next phase should either acquire confirmed negative/absence evidence or explicitly choose a method that supports positive-unlabeled or event-retrieval evaluation. Expensive model training remains out of scope until explicitly approved.",
        "",
        "## Safeguards",
        "- Raw data is not modified.",
        "- Existing processed data is not modified.",
        "- No historical disaster events are fabricated.",
        "- Label provenance is kept for audit and excluded from model features.",
        "- Target and provenance fields are excluded from model inputs.",
        "- No ML model was trained.",
    ]
    DESIGN_MD_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    frame = pd.read_csv(DAILY_FLOOD_PATH, parse_dates=["date"], low_memory=False)
    validate_source_frame(frame)
    assert_lead_day_available(frame)

    feature_schema = build_feature_schema(list(frame.columns))
    split_plan = build_split_plan(frame)
    summary = build_summary(frame, split_plan)

    DESIGN_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    feature_schema.to_csv(FEATURE_SCHEMA_PATH, index=False, encoding="utf-8")
    split_plan.to_csv(SPLIT_PLAN_PATH, index=False, encoding="utf-8")
    summary.to_csv(SUMMARY_PATH, index=False, encoding="utf-8")
    write_design_report(frame, feature_schema, split_plan)

    print("=" * 72)
    print("PHASE 5 ML DATASET DESIGN")
    print("=" * 72)
    print(f"Source rows: {len(frame):,}")
    print(f"One-day-lead eligible rows: {int(split_plan['district_days'].sum()):,}")
    print(f"Verified flood positives: {int(frame['label_status'].eq('VERIFIED_FLOOD').sum())}")
    print(f"Confirmed negatives: 0")
    print(f"Shifted baseline feature columns: {int(feature_schema['phase6_baseline_action'].str.startswith('shift_by_').sum())}")
    print(f"Design report: {DESIGN_MD_PATH}")
    print(f"Feature schema: {FEATURE_SCHEMA_PATH}")
    print(f"Temporal split plan: {SPLIT_PLAN_PATH}")
    print(f"Summary: {SUMMARY_PATH}")
    print("No raw data, processed data, synthetic labels, or ML models were created.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError) as exc:
        print(f"PHASE 5 ML DATASET DESIGN FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
