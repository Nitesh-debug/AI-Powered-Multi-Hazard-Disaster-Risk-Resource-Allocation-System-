"""Generate Phase 7 synthetic development labels from frozen weather features."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEATHER_PATH = PROJECT_ROOT / "data" / "processed" / "weather_features.csv"
OUTPUT_PATH = PROJECT_ROOT / "data" / "development" / "phase7_synthetic_development_labels.csv"
DESIGN_PATH = PROJECT_ROOT / "results" / "phase7_synthetic_label_design.md"

SYNTHETIC_LABEL_SCOPE = "SYNTHETIC_DEVELOPMENT_ONLY"
RULE_VERSION = "phase7a_v1"
TRAINING_START = pd.Timestamp("2020-01-02")
TRAINING_END = pd.Timestamp("2021-12-31")
EXPECTED_HOURLY_ROWS = 1_022_880
EXPECTED_DAILY_ROWS = 42_620
EXPECTED_DISTRICTS = 20
MIN_THRESHOLD_OBSERVATIONS = 30

LABEL_COLUMNS = [
    "synthetic_flood_dev_v1",
    "synthetic_heavy_rain_dev_v1",
    "synthetic_landslide_dev_v1",
    "synthetic_heatwave_dev_v1",
    "synthetic_coldwave_dev_v1",
    "synthetic_windstorm_dev_v1",
]

RULE_FEATURES = [
    "rain_24h",
    "rain_3d",
    "rain_7d",
    "soil_moisture_0_7cm_mean_24h",
    "soil_moisture_0_7cm_change_24h",
    "soil_moisture_28_100cm_mean_24h",
    "temperature_min_24h",
    "temperature_max_24h",
    "wind_speed_max_24h",
    "wind_gust_max_24h",
]

OUTPUT_COLUMNS = [
    "district",
    "target_date",
    "feature_reference_date",
    "synthetic_label_scope",
    "synthetic_rule_version",
    *LABEL_COLUMNS,
    "synthetic_unavailable_reason",
]

THRESHOLD_SPECS = {
    "rain_24h_q95": ("rain_24h", 0.95, "season", True),
    "rain_3d_q95": ("rain_3d", 0.95, "season", True),
    "rain_7d_q90": ("rain_7d", 0.90, "season", True),
    "soil_shallow_mean_q90": ("soil_moisture_0_7cm_mean_24h", 0.90, "season", False),
    "soil_shallow_change_q90": ("soil_moisture_0_7cm_change_24h", 0.90, "season", False),
    "soil_deep_mean_q90": ("soil_moisture_28_100cm_mean_24h", 0.90, "season", False),
    "temperature_max_q95": ("temperature_max_24h", 0.95, "month", False),
    "temperature_min_q05": ("temperature_min_24h", 0.05, "month", False),
    "wind_speed_q95": ("wind_speed_max_24h", 0.95, "season", False),
    "wind_gust_q99": ("wind_gust_max_24h", 0.99, "season", False),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def meteorological_season(month: pd.Series) -> pd.Series:
    values = np.select(
        [
            month.isin([12, 1, 2]),
            month.isin([3, 4, 5]),
            month.isin([6, 7, 8]),
            month.isin([9, 10, 11]),
        ],
        ["DJF", "MAM", "JJA", "SON"],
        default="UNKNOWN",
    )
    return pd.Series(values, index=month.index, dtype="string")


def load_weather() -> pd.DataFrame:
    usecols = ["district", "time", *RULE_FEATURES]
    frame = pd.read_csv(WEATHER_PATH, usecols=usecols, parse_dates=["time"], low_memory=False)
    if len(frame) != EXPECTED_HOURLY_ROWS:
        raise ValueError(f"Weather row count is {len(frame):,}; expected {EXPECTED_HOURLY_ROWS:,}")
    if frame["district"].nunique() != EXPECTED_DISTRICTS:
        raise ValueError(f"Weather district count is {frame['district'].nunique()}; expected {EXPECTED_DISTRICTS}")
    if frame["time"].isna().any():
        raise ValueError("Weather data contain invalid timestamps")
    if frame.duplicated(["district", "time"]).any():
        raise ValueError("Weather data contain duplicate district-time rows")
    return frame.sort_values(["district", "time"], kind="stable").reset_index(drop=True)


def build_daily_endpoints(weather: pd.DataFrame) -> pd.DataFrame:
    frame = weather.copy()
    frame["target_date"] = frame["time"].dt.normalize()
    hourly_counts = frame.groupby(["district", "target_date"], sort=False).size()
    if not hourly_counts.eq(24).all():
        invalid = hourly_counts[~hourly_counts.eq(24)].head().to_dict()
        raise ValueError(f"District-date groups must contain 24 hourly rows: {invalid}")

    daily = (
        frame.groupby(["district", "target_date"], sort=True, as_index=False)[RULE_FEATURES]
        .last()
        .sort_values(["district", "target_date"], kind="stable")
        .reset_index(drop=True)
    )
    if len(daily) != EXPECTED_DAILY_ROWS:
        raise ValueError(f"Daily endpoint row count is {len(daily):,}; expected {EXPECTED_DAILY_ROWS:,}")
    if daily.duplicated(["district", "target_date"]).any():
        raise ValueError("Daily endpoints contain duplicate district-date rows")
    daily["month"] = daily["target_date"].dt.month
    daily["season"] = meteorological_season(daily["month"])
    return daily


def threshold_lookup(
    calibration: pd.DataFrame,
    variable: str,
    quantile: float,
    group_columns: list[str],
    positive_only: bool,
) -> dict[object, float]:
    subset = calibration[[*group_columns, variable]].dropna()
    if positive_only:
        subset = subset[subset[variable] > 0]
    if subset.empty:
        return {}
    stats = subset.groupby(group_columns, sort=True)[variable].agg(
        count="count",
        threshold=lambda values: values.quantile(quantile),
    )
    qualified = stats[stats["count"] >= MIN_THRESHOLD_OBSERVATIONS]["threshold"]
    return qualified.to_dict()


def map_lookup(frame: pd.DataFrame, group_columns: list[str], lookup: dict[object, float]) -> pd.Series:
    if len(group_columns) == 1:
        return frame[group_columns[0]].map(lookup).astype(float)
    keys = pd.Series(
        list(frame[group_columns].itertuples(index=False, name=None)),
        index=frame.index,
    )
    return keys.map(lookup).astype(float)


def resolve_threshold(
    daily: pd.DataFrame,
    calibration: pd.DataFrame,
    variable: str,
    quantile: float,
    primary_stratum: str,
    positive_only: bool,
) -> pd.Series:
    if primary_stratum == "month":
        levels = [["district", "month"], ["district", "season"], ["district"]]
    elif primary_stratum == "season":
        levels = [["district", "season"], ["district"]]
    else:
        raise ValueError(f"Unsupported threshold stratum: {primary_stratum}")

    result = pd.Series(np.nan, index=daily.index, dtype=float)
    for group_columns in levels:
        lookup = threshold_lookup(
            calibration,
            variable,
            quantile,
            group_columns,
            positive_only,
        )
        mapped = map_lookup(daily, group_columns, lookup)
        result = result.fillna(mapped)
    return result


def build_thresholds(daily: pd.DataFrame) -> dict[str, pd.Series]:
    calibration = daily[daily["target_date"].between(TRAINING_START, TRAINING_END)].copy()
    if calibration.empty:
        raise ValueError("Training-period calibration data are unavailable")
    if calibration["target_date"].min() != TRAINING_START or calibration["target_date"].max() != TRAINING_END:
        raise ValueError("Calibration data do not match the documented Phase 5 training period")

    thresholds: dict[str, pd.Series] = {}
    for name, (variable, quantile, stratum, positive_only) in THRESHOLD_SPECS.items():
        thresholds[name] = resolve_threshold(
            daily,
            calibration,
            variable,
            quantile,
            stratum,
            positive_only,
        )
    return thresholds


def encode_label(available: pd.Series, trigger: pd.Series) -> pd.Series:
    result = pd.Series("UNAVAILABLE", index=available.index, dtype="string")
    result.loc[available & trigger] = "1"
    result.loc[available & ~trigger] = "0"
    return result


def append_reason(reason: pd.Series, mask: pd.Series, token: str) -> None:
    indexes = mask[mask].index
    if indexes.empty:
        return
    current = reason.loc[indexes]
    reason.loc[indexes] = np.where(current.eq(""), token, current + "|" + token)


def standard_availability(
    daily: pd.DataFrame,
    thresholds: dict[str, pd.Series],
    features: list[str],
    threshold_names: list[str],
) -> tuple[pd.Series, pd.Series]:
    available = pd.Series(True, index=daily.index)
    reason = pd.Series("", index=daily.index, dtype="string")
    for feature in features:
        missing = daily[feature].isna()
        available &= ~missing
        append_reason(reason, missing, f"missing_feature:{feature}")
    for threshold_name in threshold_names:
        missing = thresholds[threshold_name].isna()
        available &= ~missing
        append_reason(reason, missing, f"missing_threshold:{threshold_name}")
    return available, reason


def consecutive_temperature_label(
    daily: pd.DataFrame,
    threshold: pd.Series,
    feature: str,
    comparison: str,
) -> tuple[pd.Series, pd.Series]:
    current_available = daily[feature].notna() & threshold.notna()
    if comparison == "high":
        current_condition = daily[feature] >= threshold
    elif comparison == "low":
        current_condition = daily[feature] <= threshold
    else:
        raise ValueError(f"Unsupported temperature comparison: {comparison}")

    grouped = daily["district"]
    previous_date = daily.groupby(grouped, sort=False)["target_date"].shift(1)
    previous_available = current_available.groupby(grouped, sort=False).shift(1)
    previous_condition = current_condition.groupby(grouped, sort=False).shift(1)
    consecutive = previous_date.eq(daily["target_date"] - pd.Timedelta(days=1))
    available = current_available & consecutive & previous_available.fillna(False)
    trigger = current_condition & previous_condition.fillna(False)

    reason = pd.Series("", index=daily.index, dtype="string")
    append_reason(reason, daily[feature].isna(), f"missing_feature:{feature}")
    append_reason(reason, threshold.isna(), f"missing_threshold:{feature}")
    append_reason(reason, ~consecutive, "missing_prior_calendar_date")
    append_reason(
        reason,
        consecutive & ~previous_available.fillna(False),
        "prior_day_input_or_threshold_unavailable",
    )
    return encode_label(available, trigger), reason


def generate_synthetic_labels(weather: pd.DataFrame) -> pd.DataFrame:
    daily = build_daily_endpoints(weather)
    thresholds = build_thresholds(daily)
    labels: dict[str, pd.Series] = {}
    reasons: dict[str, pd.Series] = {}

    flood_features = ["rain_24h", "rain_7d", "soil_moisture_28_100cm_mean_24h"]
    flood_thresholds = ["rain_24h_q95", "rain_7d_q90", "soil_deep_mean_q90"]
    available, reason = standard_availability(daily, thresholds, flood_features, flood_thresholds)
    trigger = (
        daily["rain_24h"].gt(0)
        & daily["rain_24h"].ge(thresholds["rain_24h_q95"])
        & daily["rain_7d"].ge(thresholds["rain_7d_q90"])
        & daily["soil_moisture_28_100cm_mean_24h"].ge(thresholds["soil_deep_mean_q90"])
    )
    labels["synthetic_flood_dev_v1"] = encode_label(available, trigger)
    reasons["synthetic_flood_dev_v1"] = reason

    available, reason = standard_availability(daily, thresholds, ["rain_24h"], ["rain_24h_q95"])
    trigger = daily["rain_24h"].gt(0) & daily["rain_24h"].ge(thresholds["rain_24h_q95"])
    labels["synthetic_heavy_rain_dev_v1"] = encode_label(available, trigger)
    reasons["synthetic_heavy_rain_dev_v1"] = reason

    landslide_features = [
        "rain_3d",
        "soil_moisture_0_7cm_mean_24h",
        "soil_moisture_0_7cm_change_24h",
    ]
    landslide_thresholds = ["rain_3d_q95", "soil_shallow_mean_q90", "soil_shallow_change_q90"]
    available, reason = standard_availability(
        daily,
        thresholds,
        landslide_features,
        landslide_thresholds,
    )
    trigger = (
        daily["rain_3d"].ge(thresholds["rain_3d_q95"])
        & daily["soil_moisture_0_7cm_mean_24h"].ge(thresholds["soil_shallow_mean_q90"])
        & daily["soil_moisture_0_7cm_change_24h"].gt(0)
        & daily["soil_moisture_0_7cm_change_24h"].ge(thresholds["soil_shallow_change_q90"])
    )
    labels["synthetic_landslide_dev_v1"] = encode_label(available, trigger)
    reasons["synthetic_landslide_dev_v1"] = reason

    labels["synthetic_heatwave_dev_v1"], reasons["synthetic_heatwave_dev_v1"] = (
        consecutive_temperature_label(
            daily,
            thresholds["temperature_max_q95"],
            "temperature_max_24h",
            "high",
        )
    )
    labels["synthetic_coldwave_dev_v1"], reasons["synthetic_coldwave_dev_v1"] = (
        consecutive_temperature_label(
            daily,
            thresholds["temperature_min_q05"],
            "temperature_min_24h",
            "low",
        )
    )

    available, reason = standard_availability(
        daily,
        thresholds,
        ["wind_gust_max_24h", "wind_speed_max_24h"],
        ["wind_gust_q99", "wind_speed_q95"],
    )
    trigger = daily["wind_gust_max_24h"].ge(thresholds["wind_gust_q99"]) & daily[
        "wind_speed_max_24h"
    ].ge(thresholds["wind_speed_q95"])
    labels["synthetic_windstorm_dev_v1"] = encode_label(available, trigger)
    reasons["synthetic_windstorm_dev_v1"] = reason

    output = pd.DataFrame(
        {
            "district": daily["district"],
            "target_date": daily["target_date"],
            "feature_reference_date": daily["target_date"] - pd.Timedelta(days=1),
            "synthetic_label_scope": SYNTHETIC_LABEL_SCOPE,
            "synthetic_rule_version": RULE_VERSION,
            **labels,
        }
    )

    combined_reasons: list[str] = []
    for index in output.index:
        items = [
            f"{label}:{reasons[label].at[index]}"
            for label in LABEL_COLUMNS
            if reasons[label].at[index]
        ]
        combined_reasons.append(";".join(items))
    output["synthetic_unavailable_reason"] = combined_reasons
    return output[OUTPUT_COLUMNS]


def main() -> int:
    if not DESIGN_PATH.exists():
        raise ValueError(f"Phase 7A design is missing: {DESIGN_PATH.relative_to(PROJECT_ROOT)}")
    source_hash_before = sha256(WEATHER_PATH)
    weather = load_weather()
    output = generate_synthetic_labels(weather)
    source_hash_after = sha256(WEATHER_PATH)
    if source_hash_before != source_hash_after:
        raise ValueError("Processed weather data changed during synthetic-label generation")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    output_to_write = output.copy()
    for column in ("target_date", "feature_reference_date"):
        output_to_write[column] = pd.to_datetime(output_to_write[column]).dt.strftime("%Y-%m-%d")
    output_to_write.to_csv(OUTPUT_PATH, index=False, encoding="utf-8")

    print("=" * 72)
    print("PHASE 7B SYNTHETIC DEVELOPMENT-LABEL GENERATION")
    print("=" * 72)
    print(f"Scope: {SYNTHETIC_LABEL_SCOPE}")
    print(f"Rule version: {RULE_VERSION}")
    print(f"Calibration period: {TRAINING_START.date()} to {TRAINING_END.date()}")
    print(f"Rows: {len(output):,}")
    print(f"Districts: {output['district'].nunique()}")
    for label in LABEL_COLUMNS:
        counts = output[label].value_counts().to_dict()
        print(
            f"{label}: positives={counts.get('1', 0):,}, "
            f"zeros={counts.get('0', 0):,}, unavailable={counts.get('UNAVAILABLE', 0):,}"
        )
    print(f"Processed weather hash unchanged: {source_hash_after}")
    print(f"Output: {OUTPUT_PATH}")
    print("ML models trained: No")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"PHASE 7B GENERATION FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
