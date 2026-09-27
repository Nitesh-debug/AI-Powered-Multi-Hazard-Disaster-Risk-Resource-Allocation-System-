"""Prepare leakage-aware Phase 7C synthetic development datasets."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEATHER_PATH = PROJECT_ROOT / "data" / "processed" / "weather_features.csv"
LABEL_PATH = PROJECT_ROOT / "data" / "development" / "phase7_synthetic_development_labels.csv"
FEATURE_SCHEMA_PATH = PROJECT_ROOT / "results" / "phase5_ml_feature_schema.csv"
SPLIT_PLAN_PATH = PROJECT_ROOT / "results" / "phase5_temporal_split_plan.csv"
OUTPUT_DIR = PROJECT_ROOT / "data" / "development" / "model_ready"

SYNTHETIC_LABEL_SCOPE = "SYNTHETIC_DEVELOPMENT_ONLY"
RULE_VERSION = "phase7a_v1"
EXPECTED_DISTRICTS = 20
EXPECTED_HOURLY_ROWS = 1_022_880
EXPECTED_LABEL_ROWS = 42_620

LABEL_COLUMNS = [
    "synthetic_flood_dev_v1",
    "synthetic_heavy_rain_dev_v1",
    "synthetic_landslide_dev_v1",
    "synthetic_heatwave_dev_v1",
    "synthetic_coldwave_dev_v1",
    "synthetic_windstorm_dev_v1",
]

OUTPUT_PATHS = {
    label: OUTPUT_DIR / f"phase7c_{label}.csv.gz"
    for label in LABEL_COLUMNS
}

DAILY_AGGREGATIONS = {
    "precipitation_daily_sum": ("precipitation", "sum"),
    "rain_daily_sum": ("rain", "sum"),
    "snowfall_daily_sum": ("snowfall", "sum"),
    "temperature_2m_daily_mean": ("temperature_2m", "mean"),
    "temperature_2m_daily_min": ("temperature_2m", "min"),
    "temperature_2m_daily_max": ("temperature_2m", "max"),
    "relative_humidity_2m_daily_mean": ("relative_humidity_2m", "mean"),
    "relative_humidity_2m_daily_max": ("relative_humidity_2m", "max"),
    "wind_speed_10m_daily_mean": ("wind_speed_10m", "mean"),
    "wind_speed_10m_daily_max": ("wind_speed_10m", "max"),
    "wind_gusts_10m_daily_max": ("wind_gusts_10m", "max"),
    "soil_moisture_0_to_7cm_daily_mean": ("soil_moisture_0_to_7cm", "mean"),
    "soil_moisture_7_to_28cm_daily_mean": ("soil_moisture_7_to_28cm", "mean"),
    "soil_moisture_28_to_100cm_daily_mean": ("soil_moisture_28_to_100cm", "mean"),
    "soil_temperature_0_to_7cm_daily_mean": ("soil_temperature_0_to_7cm", "mean"),
    "soil_temperature_7_to_28cm_daily_mean": ("soil_temperature_7_to_28cm", "mean"),
    "soil_temperature_28_to_100cm_daily_mean": ("soil_temperature_28_to_100cm", "mean"),
    "snow_depth_end_of_day": ("snow_depth", "last"),
    "precipitation_3h_end_of_day": ("precipitation_3h", "last"),
    "precipitation_6h_end_of_day": ("precipitation_6h", "last"),
    "precipitation_12h_end_of_day": ("precipitation_12h", "last"),
    "precipitation_24h_end_of_day": ("precipitation_24h", "last"),
    "precipitation_3d_end_of_day": ("precipitation_3d", "last"),
    "precipitation_7d_end_of_day": ("precipitation_7d", "last"),
    "rain_3h_end_of_day": ("rain_3h", "last"),
    "rain_6h_end_of_day": ("rain_6h", "last"),
    "rain_12h_end_of_day": ("rain_12h", "last"),
    "rain_24h_end_of_day": ("rain_24h", "last"),
    "rain_3d_end_of_day": ("rain_3d", "last"),
    "rain_7d_end_of_day": ("rain_7d", "last"),
    "snowfall_24h_end_of_day": ("snowfall_24h", "last"),
    "snowfall_3d_end_of_day": ("snowfall_3d", "last"),
    "snowfall_7d_end_of_day": ("snowfall_7d", "last"),
    "snow_depth_change_24h_end_of_day": ("snow_depth_change_24h", "last"),
    "temperature_mean_6h_daily_mean": ("temperature_mean_6h", "mean"),
    "temperature_mean_12h_daily_mean": ("temperature_mean_12h", "mean"),
    "temperature_mean_24h_daily_mean": ("temperature_mean_24h", "mean"),
    "temperature_min_24h_daily_min": ("temperature_min_24h", "min"),
    "temperature_max_24h_daily_max": ("temperature_max_24h", "max"),
    "temperature_min_3d_daily_min": ("temperature_min_3d", "min"),
    "temperature_max_3d_daily_max": ("temperature_max_3d", "max"),
    "humidity_mean_6h_daily_mean": ("humidity_mean_6h", "mean"),
    "humidity_mean_12h_daily_mean": ("humidity_mean_12h", "mean"),
    "humidity_mean_24h_daily_mean": ("humidity_mean_24h", "mean"),
    "humidity_max_24h_daily_max": ("humidity_max_24h", "max"),
    "wind_speed_mean_6h_daily_mean": ("wind_speed_mean_6h", "mean"),
    "wind_speed_mean_24h_daily_mean": ("wind_speed_mean_24h", "mean"),
    "wind_speed_max_24h_daily_max": ("wind_speed_max_24h", "max"),
    "wind_gust_max_24h_daily_max": ("wind_gust_max_24h", "max"),
    "wind_gust_max_3d_daily_max": ("wind_gust_max_3d", "max"),
    "soil_moisture_0_7cm_mean_24h_daily_mean": ("soil_moisture_0_7cm_mean_24h", "mean"),
    "soil_moisture_0_7cm_lag_24h_end_of_day": ("soil_moisture_0_7cm_lag_24h", "last"),
    "soil_moisture_0_7cm_change_24h_end_of_day": ("soil_moisture_0_7cm_change_24h", "last"),
    "soil_moisture_7_28cm_mean_24h_daily_mean": ("soil_moisture_7_28cm_mean_24h", "mean"),
    "soil_moisture_7_28cm_lag_24h_end_of_day": ("soil_moisture_7_28cm_lag_24h", "last"),
    "soil_moisture_7_28cm_change_24h_end_of_day": ("soil_moisture_7_28cm_change_24h", "last"),
    "soil_moisture_28_100cm_mean_24h_daily_mean": ("soil_moisture_28_100cm_mean_24h", "mean"),
    "soil_moisture_28_100cm_lag_24h_end_of_day": ("soil_moisture_28_100cm_lag_24h", "last"),
    "soil_moisture_28_100cm_change_24h_end_of_day": ("soil_moisture_28_100cm_change_24h", "last"),
    "soil_temperature_0_7cm_mean_24h_daily_mean": ("soil_temperature_0_7cm_mean_24h", "mean"),
    "soil_temperature_7_28cm_mean_24h_daily_mean": ("soil_temperature_7_28cm_mean_24h", "mean"),
    "soil_temperature_28_100cm_mean_24h_daily_mean": ("soil_temperature_28_100cm_mean_24h", "mean"),
    "precipitation_lag_1h_end_of_day": ("precipitation_lag_1h", "last"),
    "precipitation_lag_3h_end_of_day": ("precipitation_lag_3h", "last"),
    "precipitation_lag_6h_end_of_day": ("precipitation_lag_6h", "last"),
    "precipitation_lag_24h_end_of_day": ("precipitation_lag_24h", "last"),
    "temperature_lag_24h_end_of_day": ("temperature_lag_24h", "last"),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def deterministic_mode(values: pd.Series) -> float:
    modes = values.dropna().mode()
    return modes.iloc[0] if not modes.empty else float("nan")


def load_contract() -> tuple[list[str], pd.DataFrame]:
    schema = pd.read_csv(FEATURE_SCHEMA_PATH)
    feature_columns = schema.loc[
        schema["phase6_baseline_action"].eq("shift_by_1_day"), "source_column"
    ].tolist()
    if len(feature_columns) != 68 or len(set(feature_columns)) != 68:
        raise ValueError("Phase 5 must define exactly 68 unique one-day-shifted predictors")
    if set(feature_columns) != {*DAILY_AGGREGATIONS, "weather_code_mode"}:
        raise ValueError("Daily aggregation definitions do not match the Phase 5 feature contract")

    split_plan = pd.read_csv(
        SPLIT_PLAN_PATH,
        parse_dates=["target_start_date", "target_end_date"],
    )
    if split_plan["split"].tolist() != ["train", "validation", "test"]:
        raise ValueError("Phase 5 temporal split order must be train, validation, test")
    previous_end = None
    for row in split_plan.itertuples(index=False):
        if previous_end is not None and row.target_start_date != previous_end + pd.Timedelta(days=1):
            raise ValueError("Phase 5 temporal splits must be contiguous")
        previous_end = row.target_end_date
    return feature_columns, split_plan


def load_weather() -> pd.DataFrame:
    source_columns = sorted({source for source, _ in DAILY_AGGREGATIONS.values()} | {"weather_code"})
    frame = pd.read_csv(
        WEATHER_PATH,
        usecols=["district", "time", *source_columns],
        parse_dates=["time"],
        low_memory=False,
    )
    if len(frame) != EXPECTED_HOURLY_ROWS:
        raise ValueError(f"Weather rows are {len(frame):,}; expected {EXPECTED_HOURLY_ROWS:,}")
    if frame["district"].nunique() != EXPECTED_DISTRICTS:
        raise ValueError("Weather district coverage does not match the Phase 5 contract")
    if frame["time"].isna().any() or frame.duplicated(["district", "time"]).any():
        raise ValueError("Weather keys contain invalid timestamps or duplicates")
    return frame.sort_values(["district", "time"], kind="stable").reset_index(drop=True)


def build_daily_predictors(weather: pd.DataFrame, feature_columns: list[str]) -> pd.DataFrame:
    frame = weather.copy()
    frame["feature_reference_date"] = frame["time"].dt.normalize()
    grouped = frame.groupby(["district", "feature_reference_date"], sort=True)
    hourly_counts = grouped.size()
    if not hourly_counts.eq(24).all():
        raise ValueError("Every district-date must contain exactly 24 hourly weather rows")

    named_aggregations = {
        output: pd.NamedAgg(column=source, aggfunc=aggregation)
        for output, (source, aggregation) in DAILY_AGGREGATIONS.items()
    }
    named_aggregations["weather_code_mode"] = pd.NamedAgg(
        column="weather_code", aggfunc=deterministic_mode
    )
    daily = grouped.agg(**named_aggregations).reset_index()
    daily = daily[["district", "feature_reference_date", *feature_columns]]
    if len(daily) != EXPECTED_LABEL_ROWS or daily.duplicated(
        ["district", "feature_reference_date"]
    ).any():
        raise ValueError("Daily predictor keys do not match expected district-date coverage")
    return daily


def load_labels(split_plan: pd.DataFrame) -> pd.DataFrame:
    frame = pd.read_csv(
        LABEL_PATH,
        dtype={label: "string" for label in LABEL_COLUMNS},
        parse_dates=["target_date", "feature_reference_date"],
        keep_default_na=False,
    )
    if len(frame) != EXPECTED_LABEL_ROWS:
        raise ValueError(f"Synthetic label rows are {len(frame):,}; expected {EXPECTED_LABEL_ROWS:,}")
    if frame["district"].nunique() != EXPECTED_DISTRICTS:
        raise ValueError("Synthetic label district coverage is incomplete")
    if frame.duplicated(["district", "target_date"]).any():
        raise ValueError("Synthetic labels contain duplicate district-target-date rows")
    if not frame["feature_reference_date"].eq(frame["target_date"] - pd.Timedelta(days=1)).all():
        raise ValueError("Synthetic labels violate one-day-ahead target alignment")
    if not frame["synthetic_label_scope"].eq(SYNTHETIC_LABEL_SCOPE).all():
        raise ValueError("Synthetic label scope is invalid")
    if not frame["synthetic_rule_version"].eq(RULE_VERSION).all():
        raise ValueError("Synthetic rule version is invalid")
    for label in LABEL_COLUMNS:
        if not set(frame[label].unique()) <= {"0", "1", "UNAVAILABLE"}:
            raise ValueError(f"{label} contains unsupported values")

    frame["split"] = pd.Series(pd.NA, index=frame.index, dtype="string")
    for row in split_plan.itertuples(index=False):
        mask = frame["target_date"].between(row.target_start_date, row.target_end_date)
        if frame.loc[mask, "split"].notna().any():
            raise ValueError("Phase 5 temporal splits overlap")
        frame.loc[mask, "split"] = row.split
    return frame


def prepare_hazard_dataset(
    labels: pd.DataFrame,
    daily: pd.DataFrame,
    feature_columns: list[str],
    target: str,
) -> tuple[pd.DataFrame, dict[str, object]]:
    usable = labels[target].isin(["0", "1"])
    in_split = labels["split"].notna()
    candidates = labels.loc[
        usable & in_split,
        [
            "district",
            "target_date",
            "feature_reference_date",
            "split",
            "synthetic_label_scope",
            "synthetic_rule_version",
            target,
        ],
    ].copy()
    merged = candidates.merge(
        daily,
        on=["district", "feature_reference_date"],
        how="left",
        validate="one_to_one",
        indicator=True,
    )
    if not merged["_merge"].eq("both").all():
        raise ValueError(f"{target} has target rows without prior-day weather")
    merged = merged.drop(columns="_merge")
    complete_predictors = merged[feature_columns].notna().all(axis=1)
    incomplete_predictor_rows = int((~complete_predictors).sum())
    output = merged.loc[complete_predictors].copy()
    output[target] = output[target].astype("int8")
    output = output[
        [
            "district",
            "feature_reference_date",
            "target_date",
            "split",
            "synthetic_label_scope",
            "synthetic_rule_version",
            *feature_columns,
            target,
        ]
    ].sort_values(["target_date", "district"], kind="stable", ignore_index=True)

    counts = output[target].value_counts()
    summary = {
        "target": target,
        "source_rows": len(labels),
        "source_unavailable": int(labels[target].eq("UNAVAILABLE").sum()),
        "outside_phase5_splits": int((~in_split).sum()),
        "incomplete_predictor_rows": incomplete_predictor_rows,
        "excluded_total": len(labels) - len(output),
        "rows": len(output),
        "positive": int(counts.get(1, 0)),
        "negative": int(counts.get(0, 0)),
        "districts": int(output["district"].nunique()),
        "target_start": output["target_date"].min(),
        "target_end": output["target_date"].max(),
        "feature_reference_start": output["feature_reference_date"].min(),
        "feature_reference_end": output["feature_reference_date"].max(),
        "feature_count": len(feature_columns),
        "split_counts": {
            split: int(output["split"].eq(split).sum())
            for split in ["train", "validation", "test"]
        },
        "split_positive": {
            split: int(output.loc[output["split"].eq(split), target].eq(1).sum())
            for split in ["train", "validation", "test"]
        },
    }
    return output, summary


def build_model_ready_frames() -> tuple[dict[str, pd.DataFrame], list[dict[str, object]], list[str]]:
    feature_columns, split_plan = load_contract()
    weather = load_weather()
    daily = build_daily_predictors(weather, feature_columns)
    labels = load_labels(split_plan)
    outputs: dict[str, pd.DataFrame] = {}
    summaries = []
    for target in LABEL_COLUMNS:
        outputs[target], summary = prepare_hazard_dataset(
            labels, daily, feature_columns, target
        )
        summaries.append(summary)
    return outputs, summaries, feature_columns


def write_dataset(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    writable = frame.copy()
    for column in ["feature_reference_date", "target_date"]:
        writable[column] = writable[column].dt.strftime("%Y-%m-%d")
    temporary = path.with_name(f".{path.name}.tmp")
    writable.to_csv(
        temporary,
        index=False,
        encoding="utf-8",
        compression={"method": "gzip", "compresslevel": 6, "mtime": 0},
    )
    temporary.replace(path)


def main() -> int:
    protected = [WEATHER_PATH, LABEL_PATH, FEATURE_SCHEMA_PATH, SPLIT_PLAN_PATH]
    hashes_before = {path: sha256(path) for path in protected}
    outputs, summaries, _ = build_model_ready_frames()
    if hashes_before != {path: sha256(path) for path in protected}:
        raise ValueError("An input artifact changed during dataset preparation")

    for target, frame in outputs.items():
        write_dataset(frame, OUTPUT_PATHS[target])

    print("=" * 72)
    print("PHASE 7C MODEL-READY SYNTHETIC DEVELOPMENT DATASETS")
    print("=" * 72)
    for item in summaries:
        print(
            f"{item['target']}: rows={item['rows']:,}, positives={item['positive']:,}, "
            f"negatives={item['negative']:,}, unavailable={item['source_unavailable']:,}, "
            f"excluded={item['excluded_total']:,}"
        )
    print("Predictors per dataset: 68")
    print("Synthetic scope and rule version preserved: Yes")
    print("ML models trained: No")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"PHASE 7C PREPARATION FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
