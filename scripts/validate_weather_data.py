"""Validate the raw Open-Meteo weather files without modifying them."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "open_meteo"
REPORT_PATH = PROJECT_ROOT / "results" / "weather_validation_report.csv"

START_TIMESTAMP = pd.Timestamp("2020-01-01 00:00:00")
END_TIMESTAMP = pd.Timestamp("2025-10-31 23:00:00")

EXPECTED_DISTRICTS = {
    "Jammu",
    "Srinagar",
    "Anantnag",
    "Baramulla",
    "Kupwara",
    "Pulwama",
    "Budgam",
    "Bandipora",
    "Ganderbal",
    "Doda",
    "Kathua",
    "Udhampur",
    "Rajouri",
    "Poonch",
    "Kulgam",
    "Kishtwar",
    "Ramban",
    "Reasi",
    "Samba",
    "Shopian",
}

EXPECTED_COORDINATES = {
    "Jammu": (32.73, 74.87),
    "Srinagar": (34.08, 74.80),
    "Anantnag": (33.73, 75.15),
    "Baramulla": (34.20, 74.34),
    "Kupwara": (34.53, 74.26),
    "Pulwama": (33.88, 74.92),
    "Budgam": (34.02, 74.65),
    "Bandipora": (34.42, 74.64),
    "Ganderbal": (34.23, 75.10),
    "Doda": (33.15, 75.55),
    "Kathua": (32.37, 75.52),
    "Udhampur": (32.92, 75.13),
    "Rajouri": (33.38, 74.31),
    "Poonch": (33.77, 74.09),
    "Kulgam": (33.65, 75.02),
    "Kishtwar": (33.31, 75.77),
    "Ramban": (33.25, 75.25),
    "Reasi": (33.08, 74.83),
    "Samba": (32.57, 75.12),
    "Shopian": (33.71, 74.83),
}

REQUIRED_COLUMNS = [
    "district",
    "latitude",
    "longitude",
    "time",
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "rain",
    "snowfall",
    "snow_depth",
    "weather_code",
    "wind_speed_10m",
    "wind_gusts_10m",
    "soil_temperature_0_to_7cm",
    "soil_temperature_7_to_28cm",
    "soil_temperature_28_to_100cm",
    "soil_moisture_0_to_7cm",
    "soil_moisture_7_to_28cm",
    "soil_moisture_28_to_100cm",
]

NUMERIC_COLUMNS = [column for column in REQUIRED_COLUMNS if column not in {"district", "time"}]
REPORT_COLUMNS = [
    "record_type",
    "file",
    "district",
    "row_count",
    "duplicate_rows",
    "duplicate_timestamps",
    "missing_value_cells",
    "missing_value_columns",
    "invalid_data_types",
    "min_timestamp",
    "max_timestamp",
    "required_columns_missing",
    "district_values",
    "latitude_consistent",
    "longitude_consistent",
    "coordinates_match_expected",
    "expected_start_present",
    "expected_end_present",
    "date_range_complete",
    "status",
    "errors",
]


def format_values(values: set[str]) -> str:
    return ";".join(sorted(values))


def validate_file(path: Path) -> dict[str, object]:
    filename_district = path.stem.title()
    row = {column: "" for column in REPORT_COLUMNS}
    row.update(
        {
            "record_type": "district",
            "file": path.name,
            "district": filename_district,
            "row_count": 0,
            "duplicate_rows": 0,
            "duplicate_timestamps": 0,
            "missing_value_cells": 0,
            "missing_value_columns": "",
            "invalid_data_types": "",
            "required_columns_missing": "",
            "district_values": "",
            "latitude_consistent": False,
            "longitude_consistent": False,
            "coordinates_match_expected": False,
            "expected_start_present": False,
            "expected_end_present": False,
            "date_range_complete": False,
            "status": "FAIL",
            "errors": "",
        }
    )
    errors: list[str] = []

    try:
        df = pd.read_csv(path)
    except Exception as exc:
        row["errors"] = f"read error: {exc}"
        return row

    row["row_count"] = len(df)
    missing_columns = sorted(set(REQUIRED_COLUMNS) - set(df.columns))
    row["required_columns_missing"] = format_values(set(missing_columns))
    if missing_columns:
        errors.append("missing required columns")

    if "district" in df:
        district_values = {str(value) for value in df["district"].dropna().unique()}
        row["district_values"] = format_values(district_values)
        if district_values != {filename_district}:
            errors.append("district values do not match filename")
    else:
        district_values = set()
        errors.append("district column unavailable")

    duplicate_rows = int(df.duplicated(keep=False).sum())
    row["duplicate_rows"] = duplicate_rows
    if duplicate_rows:
        errors.append("duplicate rows")

    missing_columns_with_values = set(df.columns[df.isna().any()])
    row["missing_value_cells"] = int(df.isna().sum().sum())
    row["missing_value_columns"] = format_values(missing_columns_with_values)
    if row["missing_value_cells"]:
        errors.append("missing values")

    invalid_types: list[str] = []
    for column in NUMERIC_COLUMNS:
        if column in df:
            invalid_count = int(pd.to_numeric(df[column], errors="coerce").isna().sum())
            if invalid_count:
                invalid_types.append(f"{column} ({invalid_count})")
    if "time" in df:
        parsed_time = pd.to_datetime(df["time"], errors="coerce")
        invalid_time_count = int(parsed_time.isna().sum())
        if invalid_time_count:
            invalid_types.append(f"time ({invalid_time_count})")
    else:
        parsed_time = pd.Series(dtype="datetime64[ns]")
    row["invalid_data_types"] = ";".join(invalid_types)
    if invalid_types:
        errors.append("invalid data types")

    for coordinate in ("latitude", "longitude"):
        if coordinate in df:
            numeric_coordinate = pd.to_numeric(df[coordinate], errors="coerce")
            consistent = bool(numeric_coordinate.nunique(dropna=True) == 1 and not numeric_coordinate.isna().any())
            row[f"{coordinate}_consistent"] = consistent
            if not consistent:
                errors.append(f"{coordinate} is inconsistent")

    expected_coordinates = EXPECTED_COORDINATES.get(filename_district)
    if expected_coordinates and {"latitude", "longitude"}.issubset(df.columns):
        latitude = pd.to_numeric(df["latitude"], errors="coerce")
        longitude = pd.to_numeric(df["longitude"], errors="coerce")
        row["coordinates_match_expected"] = bool(
            latitude.notna().all()
            and longitude.notna().all()
            and (latitude == expected_coordinates[0]).all()
            and (longitude == expected_coordinates[1]).all()
        )
        if not row["coordinates_match_expected"]:
            errors.append("coordinates do not match expected district coordinates")

    if not parsed_time.empty and not parsed_time.isna().all():
        valid_time = parsed_time.dropna()
        row["min_timestamp"] = valid_time.min().isoformat(sep=" ")
        row["max_timestamp"] = valid_time.max().isoformat(sep=" ")
        duplicate_timestamps = int(valid_time.duplicated(keep=False).sum())
        row["duplicate_timestamps"] = duplicate_timestamps
        row["expected_start_present"] = bool((valid_time == START_TIMESTAMP).any())
        row["expected_end_present"] = bool((valid_time == END_TIMESTAMP).any())
        row["date_range_complete"] = bool(
            row["expected_start_present"] and row["expected_end_present"]
        )
        if duplicate_timestamps:
            errors.append("duplicate timestamps")
        if not row["date_range_complete"]:
            errors.append("expected date range is incomplete")

    if not missing_columns and not errors:
        row["status"] = "PASS"
    row["errors"] = "; ".join(dict.fromkeys(errors))
    return row


def main() -> int:
    files = sorted(RAW_DIR.glob("*.csv"))
    file_districts = {path.stem.title() for path in files}
    missing_districts = EXPECTED_DISTRICTS - file_districts
    unexpected_districts = file_districts - EXPECTED_DISTRICTS
    rows = [validate_file(path) for path in files]

    total_rows = sum(int(row["row_count"]) for row in rows)
    total_missing = sum(int(row["missing_value_cells"]) for row in rows)
    total_duplicate_rows = sum(int(row["duplicate_rows"]) for row in rows)
    total_duplicate_timestamps = sum(int(row["duplicate_timestamps"]) for row in rows)
    all_date_ranges_complete = bool(rows) and all(row["date_range_complete"] for row in rows)
    passed = bool(
        len(files) == len(EXPECTED_DISTRICTS)
        and not missing_districts
        and not unexpected_districts
        and all(row["status"] == "PASS" for row in rows)
    )

    summary = {column: "" for column in REPORT_COLUMNS}
    summary.update(
        {
            "record_type": "summary",
            "file": f"{len(files)} CSV files",
            "district": "ALL",
            "row_count": total_rows,
            "duplicate_rows": total_duplicate_rows,
            "duplicate_timestamps": total_duplicate_timestamps,
            "missing_value_cells": total_missing,
            "required_columns_missing": "",
            "expected_start_present": "",
            "expected_end_present": "",
            "date_range_complete": all_date_ranges_complete,
            "status": "PASS" if passed else "FAIL",
            "errors": "; ".join(
                item
                for item in [
                    f"missing districts: {format_values(missing_districts)}" if missing_districts else "",
                    f"unexpected districts: {format_values(unexpected_districts)}" if unexpected_districts else "",
                ]
                if item
            ),
        }
    )

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows + [summary], columns=REPORT_COLUMNS).to_csv(REPORT_PATH, index=False)

    print("=" * 72)
    print("J&K RAW WEATHER DATA VALIDATION")
    print("=" * 72)
    print(f"Raw directory: {RAW_DIR}")
    print(f"Expected period: {START_TIMESTAMP} to {END_TIMESTAMP}")
    print(f"Total files: {len(files)} (expected {len(EXPECTED_DISTRICTS)})")
    print(f"Total rows: {total_rows:,}")
    district_counts = ", ".join(
        f"{row['district']}={int(row['row_count']):,}" for row in rows
    )
    print(f"Rows per district: {district_counts}")
    print(f"Missing values: {total_missing:,} cells")
    print(f"Duplicate rows: {total_duplicate_rows:,}")
    print(f"Duplicate timestamps: {total_duplicate_timestamps:,}")
    print(f"Missing districts: {format_values(missing_districts) or 'None'}")
    print(f"Unexpected districts: {format_values(unexpected_districts) or 'None'}")
    print("Date ranges:")
    for row in rows:
        print(f"  {row['district']}: {row['min_timestamp']} to {row['max_timestamp']}")
    print(f"Validation result: {'PASS' if passed else 'FAIL'}")
    print(f"Report: {REPORT_PATH}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())