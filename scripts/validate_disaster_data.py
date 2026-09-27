"""Validate documented historical disaster events without fabricating labels."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVENT_PATH = PROJECT_ROOT / "data" / "raw" / "disasters" / "historical_disasters.csv"
SOURCE_PATH = PROJECT_ROOT / "data" / "raw" / "disasters" / "disaster_sources.csv"
REPORT_PATH = PROJECT_ROOT / "results" / "disaster_validation_report.csv"

START_DATE = pd.Timestamp("2020-01-01")
END_DATE = pd.Timestamp("2025-10-31")
EXPECTED_DISTRICTS = {
    "Jammu", "Srinagar", "Anantnag", "Baramulla", "Kupwara", "Pulwama",
    "Budgam", "Bandipora", "Ganderbal", "Doda", "Kathua", "Udhampur",
    "Rajouri", "Poonch", "Kulgam", "Kishtwar", "Ramban", "Reasi",
    "Samba", "Shopian",
}
EXPECTED_TYPES = {"Flood", "Landslide", "Heatwave", "Coldwave", "Windstorm"}
EVENT_COLUMNS = [
    "event_id", "date", "district", "disaster_type", "severity",
    "description", "source_id", "source_url", "verified",
]
REPORT_COLUMNS = [
    "disaster_type", "event_count", "verified_event_count", "district_count",
    "districts", "date_start", "date_end", "source_count", "source_ids",
    "source_quality", "suitable_for_ml", "limitations",
]


def validate_events(events: pd.DataFrame, sources: pd.DataFrame) -> pd.DataFrame:
    if list(events.columns) != EVENT_COLUMNS:
        raise ValueError(f"Event columns do not match required schema: {list(events.columns)}")
    events["date"] = pd.to_datetime(events["date"], errors="coerce")
    if events["date"].isna().any():
        raise ValueError("Event data contains missing or invalid dates")
    if events["event_id"].duplicated().any():
        raise ValueError("Duplicate event_id values found")
    if events.duplicated(subset=["date", "district", "disaster_type"], keep=False).any():
        raise ValueError("Duplicate date + district + disaster_type events found")
    if not events.empty:
        if not events["district"].isin(EXPECTED_DISTRICTS).all():
            raise ValueError("Event data contains districts outside the project scope")
        if not events["disaster_type"].isin(EXPECTED_TYPES).all():
            raise ValueError("Event data contains unsupported disaster types")
        if not events["date"].between(START_DATE, END_DATE).all():
            raise ValueError("Event data contains dates outside the requested period")
        if not events["source_id"].isin(set(sources["source_id"])).all():
            raise ValueError("Event data contains unknown source_id values")

    rows = []
    for disaster_type in sorted(EXPECTED_TYPES):
        subset = events[events["disaster_type"] == disaster_type]
        source_ids = sorted(subset["source_id"].dropna().unique())
        verified_count = int(subset["verified"].astype(str).str.lower().eq("true").sum())
        rows.append(
            {
                "disaster_type": disaster_type,
                "event_count": len(subset),
                "verified_event_count": verified_count,
                "district_count": subset["district"].nunique(),
                "districts": ";".join(sorted(subset["district"].dropna().unique())),
                "date_start": subset["date"].min() if not subset.empty else "",
                "date_end": subset["date"].max() if not subset.empty else "",
                "source_count": len(source_ids),
                "source_ids": ";".join(source_ids),
                "source_quality": "No verified event records collected",
                "suitable_for_ml": "No",
                "limitations": "No accessible source inspected provided verified district/date-level event rows for this type.",
            }
        )
    return pd.DataFrame(rows, columns=REPORT_COLUMNS)


def main() -> int:
    events = pd.read_csv(EVENT_PATH, dtype=str)
    sources = pd.read_csv(SOURCE_PATH, dtype=str)
    report = validate_events(events, sources)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(REPORT_PATH, index=False, encoding="utf-8")

    print("=" * 72)
    print("J&K HISTORICAL DISASTER DATA VALIDATION")
    print("=" * 72)
    print(f"Events: {len(events)}")
    print(f"Districts represented: {events['district'].nunique()}")
    print(f"Disaster types represented: {events['disaster_type'].nunique()}")
    date_range = "Unavailable" if events.empty else f"{events['date'].min()} to {events['date'].max()}"
    print(f"Date range: {date_range}")
    print(f"Missing dates: {int(events['date'].isna().sum())}")
    print(f"Missing districts: {int(events['district'].isna().sum())}")
    print(f"Missing disaster types: {int(events['disaster_type'].isna().sum())}")
    print(f"Duplicate events: {int(events.duplicated().sum())}")
    print(f"Sources registered: {len(sources)}")
    print("Events per disaster type:")
    for _, row in report.iterrows():
        print(f"  {row['disaster_type']}: {row['event_count']}")
    print("Verified vs unverified events: 0 verified, 0 unverified")
    print(f"Report: {REPORT_PATH}")
    print("Result: No disaster type is currently suitable for supervised ML.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError) as exc:
        print(f"DISASTER DATA VALIDATION FAILED: {exc}", file=sys.stderr)
        sys.exit(1)