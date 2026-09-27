"""Build leakage-safe weather features from the merged hourly dataset."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = PROJECT_ROOT / "data" / "processed" / "jk_weather_hourly_2020_2025.csv"
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "weather_features.csv"
SUMMARY_PATH = PROJECT_ROOT / "results" / "weather_feature_summary.csv"

EXPECTED_ROWS = 1_022_880
EXPECTED_DISTRICTS = 20
EXPECTED_ROWS_PER_DISTRICT = 51_144
KEY_COLUMNS = ["district", "time"]


def add_rolling(
    frame: pd.DataFrame,
    grouped: pd.core.groupby.generic.DataFrameGroupBy,
    source: str,
    output: str,
    window: int,
    operation: str,
    features: list[str],
) -> None:
    rolling_values = grouped[source].transform(
        lambda values: getattr(
            values.rolling(window=window, min_periods=window), operation
        )()
    )
    frame[output] = rolling_values
    features.append(output)


def add_lag(
    frame: pd.DataFrame,
    grouped: pd.core.groupby.generic.DataFrameGroupBy,
    source: str,
    output: str,
    periods: int,
    features: list[str],
) -> None:
    frame[output] = grouped[source].shift(periods)
    features.append(output)


def create_features(frame: pd.DataFrame) -> list[str]:
    features: list[str] = []
    grouped = frame.groupby("district", sort=False)

    for source, prefix in (("precipitation", "precipitation"), ("rain", "rain")):
        for hours, label in ((3, "3h"), (6, "6h"), (12, "12h"), (24, "24h"), (72, "3d"), (168, "7d")):
            add_rolling(frame, grouped, source, f"{prefix}_{label}", hours, "sum", features)

    for hours, label in ((24, "24h"), (72, "3d"), (168, "7d")):
        add_rolling(frame, grouped, "snowfall", f"snowfall_{label}", hours, "sum", features)
    add_lag(frame, grouped, "snow_depth", "snow_depth_change_24h", 24, features)
    frame["snow_depth_change_24h"] = frame["snow_depth"] - frame["snow_depth_change_24h"]

    for hours, label in ((6, "6h"), (12, "12h"), (24, "24h")):
        add_rolling(frame, grouped, "temperature_2m", f"temperature_mean_{label}", hours, "mean", features)
    for hours, label in ((24, "24h"), (72, "3d")):
        add_rolling(frame, grouped, "temperature_2m", f"temperature_min_{label}", hours, "min", features)
        add_rolling(frame, grouped, "temperature_2m", f"temperature_max_{label}", hours, "max", features)

    for hours, label in ((6, "6h"), (12, "12h"), (24, "24h")):
        add_rolling(frame, grouped, "relative_humidity_2m", f"humidity_mean_{label}", hours, "mean", features)
    add_rolling(frame, grouped, "relative_humidity_2m", "humidity_max_24h", 24, "max", features)

    for hours, label in ((6, "6h"), (24, "24h")):
        add_rolling(frame, grouped, "wind_speed_10m", f"wind_speed_mean_{label}", hours, "mean", features)
    add_rolling(frame, grouped, "wind_speed_10m", "wind_speed_max_24h", 24, "max", features)
    add_rolling(frame, grouped, "wind_gusts_10m", "wind_gust_max_24h", 24, "max", features)
    add_rolling(frame, grouped, "wind_gusts_10m", "wind_gust_max_3d", 72, "max", features)

    soil_moisture_columns = {
        "soil_moisture_0_to_7cm": "soil_moisture_0_7cm",
        "soil_moisture_7_to_28cm": "soil_moisture_7_28cm",
        "soil_moisture_28_to_100cm": "soil_moisture_28_100cm",
    }
    for source, label in soil_moisture_columns.items():
        add_rolling(frame, grouped, source, f"{label}_mean_24h", 24, "mean", features)
        add_lag(frame, grouped, source, f"{label}_lag_24h", 24, features)
        frame[f"{label}_change_24h"] = frame[source] - frame[f"{label}_lag_24h"]
        features.append(f"{label}_change_24h")

    soil_temperature_columns = {
        "soil_temperature_0_to_7cm": "soil_temperature_0_7cm",
        "soil_temperature_7_to_28cm": "soil_temperature_7_28cm",
        "soil_temperature_28_to_100cm": "soil_temperature_28_100cm",
    }
    for source, label in soil_temperature_columns.items():
        add_rolling(frame, grouped, source, f"{label}_mean_24h", 24, "mean", features)

    frame["hour"] = frame["time"].dt.hour
    frame["day_of_week"] = frame["time"].dt.dayofweek
    frame["day_of_year"] = frame["time"].dt.dayofyear
    frame["month"] = frame["time"].dt.month
    frame["year"] = frame["time"].dt.year
    frame["hour_sin"] = np.sin(2 * np.pi * frame["hour"] / 24)
    frame["hour_cos"] = np.cos(2 * np.pi * frame["hour"] / 24)
    frame["month_sin"] = np.sin(2 * np.pi * (frame["month"] - 1) / 12)
    frame["month_cos"] = np.cos(2 * np.pi * (frame["month"] - 1) / 12)
    features.extend(
        [
            "hour",
            "day_of_week",
            "day_of_year",
            "month",
            "year",
            "hour_sin",
            "hour_cos",
            "month_sin",
            "month_cos",
        ]
    )

    for periods, label in ((1, "1h"), (3, "3h"), (6, "6h"), (24, "24h")):
        add_lag(frame, grouped, "precipitation", f"precipitation_lag_{label}", periods, features)
    add_lag(frame, grouped, "temperature_2m", "temperature_lag_24h", 24, features)
    return features


def feature_summary(frame: pd.DataFrame) -> pd.DataFrame:
    summary = []
    total_rows = len(frame)
    for column in frame.columns:
        values = frame[column]
        missing_count = int(values.isna().sum())
        item = {
            "feature_name": column,
            "dtype": str(values.dtype),
            "missing_count": missing_count,
            "missing_percentage": missing_count / total_rows * 100,
            "min": "",
            "max": "",
            "mean": "",
            "std": "",
        }
        if pd.api.types.is_numeric_dtype(values):
            item.update(
                {
                    "min": values.min(),
                    "max": values.max(),
                    "mean": values.mean(),
                    "std": values.std(),
                }
            )
        elif pd.api.types.is_datetime64_any_dtype(values):
            item.update({"min": values.min(), "max": values.max()})
        else:
            item.update({"min": values.min(), "max": values.max()})
        summary.append(item)
    return pd.DataFrame(summary)


def main() -> int:
    frame = pd.read_csv(INPUT_PATH, parse_dates=["time"])
    if frame["time"].isna().any():
        raise ValueError("Input contains invalid timestamps")
    frame = frame.sort_values(["district", "time"], kind="stable").reset_index(drop=True)

    input_rows = len(frame)
    input_districts = frame["district"].nunique()
    if input_rows != EXPECTED_ROWS:
        raise ValueError(f"Input row count is {input_rows:,}; expected {EXPECTED_ROWS:,}")
    if input_districts != EXPECTED_DISTRICTS:
        raise ValueError(f"Input district count is {input_districts}; expected {EXPECTED_DISTRICTS}")
    if frame.duplicated(KEY_COLUMNS).any():
        raise ValueError("Input contains duplicate district + time rows")

    original_columns = list(frame.columns)
    new_features = create_features(frame)
    if len(new_features) != len(set(new_features)):
        raise ValueError("Feature generation produced duplicate feature names")

    if len(frame) != input_rows:
        raise ValueError("Feature engineering changed the number of rows")
    if frame.duplicated(KEY_COLUMNS).any():
        raise ValueError("Feature output contains duplicate district + time rows")

    counts = frame.groupby("district", sort=True).size()
    invalid_counts = counts[counts != EXPECTED_ROWS_PER_DISTRICT]
    if not invalid_counts.empty:
        raise ValueError(f"Invalid output district row counts: {invalid_counts.to_dict()}")

    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(OUTPUT_PATH, index=False, encoding="utf-8")
    feature_summary(frame).to_csv(SUMMARY_PATH, index=False, encoding="utf-8")

    missing = frame.isna().sum()
    missing = missing[missing > 0].sort_values(ascending=False)
    print("=" * 72)
    print("J&K WEATHER FEATURE ENGINEERING")
    print("=" * 72)
    print(f"Input rows: {input_rows:,}")
    print(f"Total rows: {len(frame):,}")
    print(f"Total columns: {len(frame.columns)}")
    print(f"Original columns: {len(original_columns)}")
    print(f"New features: {len(new_features)}")
    print(f"District count: {frame['district'].nunique()}")
    print(f"Rows per district: {counts.to_dict()}")
    print(f"Timestamp range: {frame['time'].min()} to {frame['time'].max()}")
    print(f"Duplicate district + time rows: {int(frame.duplicated(KEY_COLUMNS).sum()):,}")
    print(f"Total missing values: {int(frame.isna().sum().sum()):,}")
    if missing.empty:
        print("Missing-value detail: None")
    else:
        print("Missing-value detail:")
        for column, count in missing.items():
            print(f"  {column}: {int(count):,} ({count / len(frame) * 100:.4f}%)")
    print(f"Feature names: {', '.join(new_features)}")
    print(f"Output: {OUTPUT_PATH}")
    print(f"Feature summary: {SUMMARY_PATH}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError) as exc:
        print(f"FEATURE ENGINEERING FAILED: {exc}", file=sys.stderr)
        sys.exit(1)