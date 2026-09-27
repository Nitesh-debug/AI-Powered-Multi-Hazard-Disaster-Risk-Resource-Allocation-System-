"""Merge validated raw district weather files into one processed CSV."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

try:
    from scripts.validate_weather_data import (
        END_TIMESTAMP,
        EXPECTED_COORDINATES,
        EXPECTED_DISTRICTS,
        REQUIRED_COLUMNS,
        START_TIMESTAMP,
    )
except ModuleNotFoundError:
    from validate_weather_data import (
        END_TIMESTAMP,
        EXPECTED_COORDINATES,
        EXPECTED_DISTRICTS,
        REQUIRED_COLUMNS,
        START_TIMESTAMP,
    )


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "open_meteo"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_PATH = PROCESSED_DIR / "jk_weather_hourly_2020_2025.csv"
SUMMARY_PATH = PROJECT_ROOT / "results" / "merged_weather_summary.csv"

EXPECTED_ROWS_PER_DISTRICT = 51_144
EXPECTED_TOTAL_ROWS = len(EXPECTED_DISTRICTS) * EXPECTED_ROWS_PER_DISTRICT


def fail(message: str) -> None:
    raise ValueError(message)


def read_and_validate_file(path: Path) -> pd.DataFrame:
    expected_district = path.stem.title()
    try:
        frame = pd.read_csv(path)
    except Exception as exc:
        fail(f"Could not read {path.name}: {exc}")

    missing_columns = sorted(set(REQUIRED_COLUMNS) - set(frame.columns))
    if missing_columns:
        fail(f"{path.name} is missing required columns: {', '.join(missing_columns)}")

    if set(frame.columns) != set(REQUIRED_COLUMNS):
        extra_columns = sorted(set(frame.columns) - set(REQUIRED_COLUMNS))
        fail(f"{path.name} contains unexpected columns: {', '.join(extra_columns)}")

    district_values = set(frame["district"].dropna().astype(str).unique())
    if district_values != {expected_district}:
        fail(
            f"{path.name} district values {sorted(district_values)} "
            f"do not match filename district {expected_district}"
        )

    frame["time"] = pd.to_datetime(frame["time"], errors="coerce")
    if frame["time"].isna().any():
        fail(f"{path.name} contains invalid timestamps")
    if frame.isna().any().any():
        missing_count = int(frame.isna().sum().sum())
        fail(f"{path.name} contains {missing_count} missing values")

    expected_coordinates = EXPECTED_COORDINATES[expected_district]
    if frame["latitude"].nunique() != 1 or frame["longitude"].nunique() != 1:
        fail(f"{path.name} has inconsistent latitude/longitude values")
    if not (
        frame["latitude"].iloc[0] == expected_coordinates[0]
        and frame["longitude"].iloc[0] == expected_coordinates[1]
    ):
        fail(f"{path.name} coordinates do not match expected district coordinates")

    if len(frame) != EXPECTED_ROWS_PER_DISTRICT:
        fail(
            f"{path.name} has {len(frame):,} rows; "
            f"expected {EXPECTED_ROWS_PER_DISTRICT:,}"
        )
    if frame["time"].min() != START_TIMESTAMP or frame["time"].max() != END_TIMESTAMP:
        fail(
            f"{path.name} date range is {frame['time'].min()} to {frame['time'].max()}; "
            f"expected {START_TIMESTAMP} to {END_TIMESTAMP}"
        )

    return frame[REQUIRED_COLUMNS]


def main() -> int:
    files = sorted(RAW_DIR.glob("*.csv"))
    file_districts = {path.stem.title() for path in files}
    missing_districts = EXPECTED_DISTRICTS - file_districts
    unexpected_districts = file_districts - EXPECTED_DISTRICTS
    if missing_districts or unexpected_districts or len(files) != len(EXPECTED_DISTRICTS):
        fail(
            "Raw district file validation failed: "
            f"missing={sorted(missing_districts)}, "
            f"unexpected={sorted(unexpected_districts)}, "
            f"file_count={len(files)}"
        )

    frames = [read_and_validate_file(path) for path in files]
    merged = pd.concat(frames, ignore_index=True)
    merged = merged.sort_values(["district", "time"], kind="stable").reset_index(drop=True)

    duplicate_mask = merged.duplicated(subset=["district", "time"], keep=False)
    duplicate_count = int(duplicate_mask.sum())
    if duplicate_count:
        fail(
            f"Found {duplicate_count:,} duplicate district+time rows; "
            "no rows were removed"
        )

    if len(merged) != EXPECTED_TOTAL_ROWS:
        fail(f"Merged row count is {len(merged):,}; expected {EXPECTED_TOTAL_ROWS:,}")

    counts = merged.groupby("district", sort=True).size()
    invalid_counts = counts[counts != EXPECTED_ROWS_PER_DISTRICT]
    if not invalid_counts.empty:
        fail(f"Invalid district row counts: {invalid_counts.to_dict()}")

    summary_rows = []
    for district, district_frame in merged.groupby("district", sort=True):
        summary_rows.append(
            {
                "district": district,
                "row_count": len(district_frame),
                "min_time": district_frame["time"].min(),
                "max_time": district_frame["time"].max(),
                "latitude": district_frame["latitude"].iloc[0],
                "longitude": district_frame["longitude"].iloc[0],
            }
        )

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(OUTPUT_PATH, index=False, encoding="utf-8")
    pd.DataFrame(summary_rows).to_csv(SUMMARY_PATH, index=False, encoding="utf-8")

    print("=" * 72)
    print("J&K HISTORICAL WEATHER DATA MERGE")
    print("=" * 72)
    print(f"Input files: {len(files)}")
    print(f"Rows before merge: {sum(len(frame) for frame in frames):,}")
    print(f"Rows after merge: {len(merged):,}")
    print(f"Total columns: {len(merged.columns)}")
    print(f"District count: {merged['district'].nunique()}")
    print("Rows per district:")
    for district, count in counts.items():
        print(f"  {district}: {count:,}")
    print(f"Date range: {merged['time'].min()} to {merged['time'].max()}")
    print(f"Duplicate district+time rows: {duplicate_count:,}")
    print(f"Missing values: {int(merged.isna().sum().sum()):,}")
    print(f"Columns: {', '.join(merged.columns)}")
    print(f"Output file size: {OUTPUT_PATH.stat().st_size:,} bytes")
    print(f"Merged dataset: {OUTPUT_PATH}")
    print(f"Summary report: {SUMMARY_PATH}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError) as exc:
        print(f"MERGE FAILED: {exc}", file=sys.stderr)
        sys.exit(1)