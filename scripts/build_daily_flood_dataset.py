"""Build a daily weather dataset with verified flood-event provenance."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEATHER_PATH = PROJECT_ROOT / "data" / "processed" / "weather_features.csv"
EVENT_PATH = PROJECT_ROOT / "data" / "raw" / "disasters" / "curated_flood_events.csv"
RAW_WEATHER_DIR = PROJECT_ROOT / "data" / "raw" / "open_meteo"
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "daily_flood_dataset.csv"
SUMMARY_PATH = PROJECT_ROOT / "results" / "daily_flood_dataset_summary.csv"
REPORT_PATH = PROJECT_ROOT / "results" / "daily_flood_label_report.md"

EXPECTED_EVENT_RECORDS = 29
EXPECTED_POSITIVE_COMBINATIONS = 32
PROJECT_DISTRICTS = {
    "Jammu", "Srinagar", "Anantnag", "Baramulla", "Kupwara", "Pulwama",
    "Budgam", "Bandipora", "Ganderbal", "Doda", "Kathua", "Udhampur",
    "Rajouri", "Poonch", "Kulgam", "Kishtwar", "Ramban", "Reasi",
    "Samba", "Shopian",
}


def clean(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def district_tokens(value: object) -> list[str]:
    return [token.strip() for token in clean(value).split(",") if token.strip()]


def daily_aggregation(frame: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    frame = frame.copy()
    frame["date"] = frame["time"].dt.normalize()
    grouped = frame.groupby(["district", "date"], sort=True)
    result = grouped[["latitude", "longitude"]].first().reset_index()
    rules: list[str] = []

    def add(column: str, aggregation: str, output: str) -> None:
        result[output] = grouped[column].agg(aggregation).reset_index(drop=True)
        rules.append(f"{output}: {column} {aggregation}")

    for column in ("precipitation", "rain", "snowfall"):
        add(column, "sum", f"{column}_daily_sum")

    for column in ("temperature_2m",):
        add(column, "mean", f"{column}_daily_mean")
        add(column, "min", f"{column}_daily_min")
        add(column, "max", f"{column}_daily_max")
    add("relative_humidity_2m", "mean", "relative_humidity_2m_daily_mean")
    add("relative_humidity_2m", "max", "relative_humidity_2m_daily_max")
    add("wind_speed_10m", "mean", "wind_speed_10m_daily_mean")
    add("wind_speed_10m", "max", "wind_speed_10m_daily_max")
    add("wind_gusts_10m", "max", "wind_gusts_10m_daily_max")

    for column in ("soil_moisture_0_to_7cm", "soil_moisture_7_to_28cm", "soil_moisture_28_to_100cm"):
        add(column, "mean", f"{column}_daily_mean")
    for column in ("soil_temperature_0_to_7cm", "soil_temperature_7_to_28cm", "soil_temperature_28_to_100cm"):
        add(column, "mean", f"{column}_daily_mean")
    add("snow_depth", "last", "snow_depth_end_of_day")

    excluded = {
        "district", "latitude", "longitude", "time", "date", "weather_code",
        "temperature_2m", "relative_humidity_2m", "precipitation", "rain", "snowfall",
        "snow_depth", "wind_speed_10m", "wind_gusts_10m",
        "soil_temperature_0_to_7cm", "soil_temperature_7_to_28cm", "soil_temperature_28_to_100cm",
        "soil_moisture_0_to_7cm", "soil_moisture_7_to_28cm", "soil_moisture_28_to_100cm",
        "hour", "day_of_week", "day_of_year", "month", "year", "hour_sin", "hour_cos", "month_sin", "month_cos",
    }
    for column in frame.columns:
        if column in excluded:
            continue
        if column.startswith(("precipitation_", "rain_", "snowfall_")):
            add(column, "last", f"{column}_end_of_day")
        elif any(token in column for token in ("_mean_", "_min_", "_max_")):
            aggregation = "min" if "_min_" in column else "max" if "_max_" in column else "mean"
            add(column, aggregation, f"{column}_daily_{aggregation}")
        else:
            add(column, "last", f"{column}_end_of_day")

    def daily_mode(values: pd.Series) -> object:
        modes = values.dropna().mode()
        return modes.iloc[0] if not modes.empty else pd.NA

    result["weather_code_mode"] = grouped["weather_code"].agg(daily_mode).reset_index(drop=True)
    rules.append("weather_code_mode: daily mode; categorical codes are never averaged")
    return result, rules


def add_event_labels(daily: pd.DataFrame, events: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    events = events[events["flood_label_status"] == "EXPLICIT_FLOOD"].copy()
    if len(events) != EXPECTED_EVENT_RECORDS:
        raise ValueError(f"Expected {EXPECTED_EVENT_RECORDS} explicit event records, found {len(events)}")
    events["date"] = pd.to_datetime(events["date"], errors="coerce").dt.normalize()
    if events["date"].isna().any():
        raise ValueError("Explicit flood events contain invalid dates")

    positive_rows = []
    for _, event in events.iterrows():
        districts = district_tokens(event["district"])
        if not districts or not set(districts).issubset(PROJECT_DISTRICTS):
            raise ValueError(f"Unresolved project district in event {event['event_id']}: {event['district']}")
        for district in districts:
            positive_rows.append(
                {
                    "district": district,
                    "date": event["date"],
                    "flood_event_label": 1,
                    "label_status": "VERIFIED_FLOOD",
                    "label_source": event["source"],
                    "label_source_url": event["source_url"],
                    "flood_event_ids": event["event_id"],
                }
            )
    positives = pd.DataFrame(positive_rows).drop_duplicates(["district", "date"])
    if len(positives) != EXPECTED_POSITIVE_COMBINATIONS:
        raise ValueError(f"Expected {EXPECTED_POSITIVE_COMBINATIONS} positive combinations, found {len(positives)}")
    if positives.duplicated(["district", "date"]).any():
        raise ValueError("Duplicate positive district-date combinations found")

    output = daily.merge(positives, on=["district", "date"], how="left", validate="one_to_one")
    unknown = output["label_status"].isna()
    output.loc[unknown, "label_status"] = "NO_VERIFIED_EVENT"
    output.loc[unknown, "label_source"] = "NOT_ESTABLISHED"
    output["flood_event_label"] = output["flood_event_label"].astype("Int64")
    return output, positives


def main() -> int:
    raw_mtimes_before = {path: path.stat().st_mtime_ns for path in RAW_WEATHER_DIR.glob("*.csv")}
    weather = pd.read_csv(WEATHER_PATH, parse_dates=["time"])
    if weather["time"].isna().any():
        raise ValueError("Weather features contain invalid timestamps")
    if weather.duplicated(["district", "time"]).any():
        raise ValueError("Weather features contain duplicate district-time rows")
    daily, aggregation_rules = daily_aggregation(weather)
    events = pd.read_csv(EVENT_PATH)
    output, positives = add_event_labels(daily, events)
    output = output.sort_values(["district", "date"]).reset_index(drop=True)

    if output.duplicated(["district", "date"]).any():
        raise ValueError("Daily output contains duplicate district-date rows")
    if len(output) != len(daily):
        raise ValueError("Label join changed the daily row count")
    raw_mtimes_after = {path: path.stat().st_mtime_ns for path in RAW_WEATHER_DIR.glob("*.csv")}
    if raw_mtimes_before != raw_mtimes_after:
        raise ValueError("Raw Open-Meteo file timestamps changed")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(OUTPUT_PATH, index=False, encoding="utf-8", date_format="%Y-%m-%d")

    positive_count = int(output["label_status"].eq("VERIFIED_FLOOD").sum())
    unknown_count = int(output["label_status"].eq("NO_VERIFIED_EVENT").sum())
    summary = pd.DataFrame(
        [
            ("total_district_days", len(output)),
            ("verified_flood_positive_district_days", positive_count),
            ("unknown_no_verified_event_days", unknown_count),
            ("district_count", output["district"].nunique()),
            ("verified_event_district_count", positives["district"].nunique()),
            ("earliest_date", output["date"].min().strftime("%Y-%m-%d")),
            ("latest_date", output["date"].max().strftime("%Y-%m-%d")),
            ("duplicate_district_date_rows", int(output.duplicated(["district", "date"]).sum())),
            ("missing_value_cells", int(output.isna().sum().sum())),
            ("verified_event_records_used", EXPECTED_EVENT_RECORDS),
            ("normalized_positive_combinations", EXPECTED_POSITIVE_COMBINATIONS),
        ],
        columns=["metric", "value"],
    )
    summary.to_csv(SUMMARY_PATH, index=False, encoding="utf-8")

    missing = output.isna().sum()
    missing = missing[missing > 0].sort_values(ascending=False)
    district_counts = positives.groupby("district").size().sort_index()
    event_dates = positives.groupby("date").size().sort_index()
    report_lines = [
        "# Daily Flood Dataset Report",
        "",
        "## Construction",
        f"Built from `weather_features.csv` ({len(weather):,} hourly rows) and the curated IFI event file. The weather data was aggregated to {len(output):,} district-day rows.",
        "",
        "Aggregation rules:",
        *[f"- {rule}" for rule in aggregation_rules],
        "- Hourly calendar/cyclical features were omitted; calendar fields can be derived directly from `date`.",
        "- Lag and rolling features are retained as end-of-day values because they represent the information available at the final hour of that date; they are not treated as daily sums.",
        "",
        "## Label semantics",
        f"- `VERIFIED_FLOOD`: {positive_count} district-date combinations supported by explicit IFI flood records.",
        f"- `NO_VERIFIED_EVENT`: {unknown_count} district-days without a verified event record. These are **unknown/not-established**, not confirmed flood negatives; `flood_event_label` remains missing for them.",
        f"- Exactly {EXPECTED_POSITIVE_COMBINATIONS} positive combinations were normalized from {EXPECTED_EVENT_RECORDS} source event records.",
        "- No dates before or after a documented event date were expanded.",
        "",
        "## Coverage",
        f"- Districts in weather data: {output['district'].nunique()}",
        f"- Districts with verified flood events: {positives['district'].nunique()} ({', '.join(sorted(positives['district'].unique()))})",
        f"- Date range: {output['date'].min():%Y-%m-%d} to {output['date'].max():%Y-%m-%d}",
        f"- Positive district-days per district: {district_counts.to_dict()}",
        f"- Multiple positive event records on the same date: {event_dates[event_dates > 1].to_dict()}",
        "",
        "## Missing values",
        f"Total missing cells: {int(output.isna().sum().sum()):,}. Missing values are retained from feature warm-up windows and from the intentionally unknown flood labels.",
        "",
        "## Validation",
        "- Duplicate district-date combinations: 0.",
        f"- Verified positive district-date combinations: {positive_count} (expected {EXPECTED_POSITIVE_COMBINATIONS}).",
        "- Raw Open-Meteo file modification timestamps were unchanged during execution.",
        "- No ML model was trained.",
        "- No synthetic flood labels were created.",
        "- No event dates were expanded beyond the documented event date.",
        "",
        "## Limitation",
        "The verified event source covers only part of the weather period and only 15 districts in the explicit-event subset. An unrecorded date is not established as flood-free. This daily dataset is therefore appropriate for documented positive-event analysis, not for treating all remaining rows as confirmed negatives.",
    ]
    if not missing.empty:
        report_lines.extend(["", "Missing-value columns:"] + [f"- `{column}`: {int(count):,}" for column, count in missing.items()])
    REPORT_PATH.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print("=" * 72)
    print("DAILY FLOOD DATASET")
    print("=" * 72)
    print(f"Total district-days: {len(output):,}")
    print(f"Verified flood-positive district-days: {positive_count}")
    print(f"Unknown/no verified-event days: {unknown_count}")
    print(f"Districts in weather data: {output['district'].nunique()}")
    print(f"Districts with verified events: {positives['district'].nunique()}")
    print(f"Date range: {output['date'].min():%Y-%m-%d} to {output['date'].max():%Y-%m-%d}")
    print(f"Duplicate district-date rows: {int(output.duplicated(['district', 'date']).sum())}")
    print(f"Missing-value cells: {int(output.isna().sum().sum()):,}")
    print(f"Output: {OUTPUT_PATH}")
    print(f"Summary: {SUMMARY_PATH}")
    print(f"Report: {REPORT_PATH}")
    print("No binary negative labels, hourly labels, weather merges beyond daily aggregation, or models were created.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError) as exc:
        print(f"DAILY FLOOD DATASET FAILED: {exc}", file=sys.stderr)
        sys.exit(1)