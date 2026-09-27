"""Analyze explicit IFI flood events for a defensible label design."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = PROJECT_ROOT / "data" / "raw" / "disasters" / "curated_flood_events.csv"
ANALYSIS_PATH = PROJECT_ROOT / "results" / "flood_event_analysis.csv"
REPORT_PATH = PROJECT_ROOT / "results" / "flood_label_design_report.md"
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


def markdown_table(frame: pd.DataFrame, columns: list[str]) -> str:
    if frame.empty:
        return "_None._"
    output = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for _, row in frame[columns].iterrows():
        output.append("| " + " | ".join(str(row[column]).replace("|", "\\|") for column in columns) + " |")
    return "\n".join(output)


def main() -> int:
    events = pd.read_csv(INPUT_PATH)
    events = events[events["flood_label_status"] == "EXPLICIT_FLOOD"].copy()
    if len(events) != 29:
        raise ValueError(f"Expected 29 explicit flood records, found {len(events)}")

    events["date"] = pd.to_datetime(events["date"], errors="coerce")
    if events["date"].isna().any():
        raise ValueError("Explicit flood records contain missing or invalid dates")

    events["district_list"] = events["district"].map(district_tokens)
    events["district_scope"] = events["district_list"].map(
        lambda values: "MULTI_DISTRICT" if len(values) > 1 else "SINGLE_DISTRICT"
    )
    events["district_mapping_status"] = events["district_list"].map(
        lambda values: "RESOLVED_SOURCE_LIST" if values and set(values).issubset(PROJECT_DISTRICTS) else "UNRESOLVED"
    )
    events["duration_status"] = "UNAVAILABLE_IN_CURATED_INPUT"
    events["severity_status"] = events["severity"].map(
        lambda value: "AVAILABLE" if clean(value) else "MISSING"
    )
    events["impact_status"] = events["original_description"].map(
        lambda value: "DESCRIPTION_AVAILABLE" if clean(value) else "NO_DESCRIPTION"
    )
    events["event_day_label_supported"] = True
    events["event_window_label_supported"] = False

    analysis_columns = [
        "event_id", "date", "district", "severity", "original_description",
        "original_cause", "source", "district_scope", "district_mapping_status",
        "duration_status", "severity_status", "impact_status",
        "event_day_label_supported", "event_window_label_supported",
    ]
    analysis = events[analysis_columns].sort_values(["date", "district", "event_id"])

    expanded_rows = []
    for _, event in events.iterrows():
        for district in event["district_list"]:
            expanded_rows.append({"event_id": event["event_id"], "date": event["date"], "district": district})
    expanded = pd.DataFrame(expanded_rows).drop_duplicates()
    if len(expanded) != 32:
        raise ValueError(f"Expected 32 normalized event-date/district combinations, found {len(expanded)}")

    same_date = events.groupby("date").agg(event_count=("event_id", "nunique"), event_ids=("event_id", lambda values: ";".join(values)))
    same_date = same_date[same_date["event_count"] > 1].reset_index()
    multi_events = events[events["district_scope"] == "MULTI_DISTRICT"][
        ["event_id", "date", "district", "district_mapping_status"]
    ]

    events_per_district = expanded.groupby("district").size().rename("event_date_combinations").reset_index()
    events_per_year = events.groupby(events["date"].dt.year).size().rename("event_records").rename_axis("year").reset_index()
    events_per_month = events.groupby(events["date"].dt.month).size().rename("event_records").rename_axis("month").reset_index()

    severity_available = int((events["severity_status"] == "AVAILABLE").sum())
    descriptions_available = int((events["impact_status"] == "DESCRIPTION_AVAILABLE").sum())
    source_counts = events["source"].replace("", pd.NA).dropna().value_counts().to_dict()

    analysis.to_csv(ANALYSIS_PATH, index=False, encoding="utf-8", date_format="%Y-%m-%d")
    REPORT_PATH.write_text(
        "\n".join(
            [
                "# Flood Label Design Report",
                "",
                "## Scope",
                "This analysis uses only the 29 `EXPLICIT_FLOOD` records from the curated IFI-Impacts v4 subset. It does not read weather values, create labels, or modify any weather dataset.",
                "",
                "## What the source provides",
                f"The input provides {len(events)} event records dated {events['date'].min():%Y-%m-%d} through {events['date'].max():%Y-%m-%d}. Each record has an event ID, source date, source district text, original cause wording, source, and LGD code field. All records identify IMD as the event source.",
                f"There are {len(multi_events)} multi-district records. Their district strings contain explicit project-district names and can be deterministically tokenized into {len(expanded)} event-date/district combinations without assigning an event to an unlisted district.",
                "",
                "## Missing information",
                f"The curated input contains no usable start/end duration fields, so duration is unavailable for all {len(events)} records. Severity is missing for {len(events) - severity_available} records ({severity_available} available). Only {descriptions_available} records contain a non-empty original description/impact text. The source does not establish hourly onset or end times.",
                "",
                "## Label strategy recommendation",
                "**Recommend Option A: event-day labeling, subject to a later explicit implementation decision.** For each source event date and each district explicitly listed by that source record, one daily event occurrence is supported. The three multi-district records can be expanded to their listed districts while retaining the same event ID and a multi-district provenance flag.",
                "",
                "Option B (event-duration labeling) is not supported because the curated input does not provide event duration. Do not infer duration from weather, neighboring dates, or the `Duration(Days)` field omitted from this curated input.",
                "",
                "Option C (event-window labeling) is not recommended for the ground-truth event label. A pre-event or post-event window would be a separate modeling feature/response design and must not be represented as an observed flood date without additional source evidence.",
                "",
                f"Under the recommended event-day design, the data would produce **{len(expanded)} positive event-date/district combinations** from {len(events)} source records. This report does not create those labels in the hourly weather data.",
                "",
                "## Events per district",
                markdown_table(events_per_district, ["district", "event_date_combinations"]),
                "",
                "## Events per year",
                markdown_table(events_per_year, ["year", "event_records"]),
                "",
                "## Events per month",
                markdown_table(events_per_month, ["month", "event_records"]),
                "",
                "## Multiple event records on the same date",
                markdown_table(same_date, ["date", "event_count", "event_ids"]),
                "",
                "## Multi-district records",
                markdown_table(multi_events, ["event_id", "date", "district", "district_mapping_status"]),
                "",
                "## Limitations",
                "The records cover only 2020–2023, omit Jammu, are sparse for supervised learning, and lack hourly timing and severity values. Several source events share dates or affect multiple districts. Any later hourly alignment must document the choice of date boundary and timezone; it must not imply that adjacent hours or dates were observed flood periods.",
                "",
                "## Proceed decision",
                "The curated records are sufficient to prototype a documented event-day alignment process, but they are not sufficient to claim complete or balanced flood ground truth for all 20 districts or the full 2020–2025 weather period. No model training should begin until the event-day expansion and handling of missing district/date coverage are approved.",
            ]
        ),
        encoding="utf-8",
    )

    print("=" * 72)
    print("EXPLICIT FLOOD EVENT ANALYSIS")
    print("=" * 72)
    print(f"Explicit flood records: {len(events)}")
    print(f"Date range: {events['date'].min():%Y-%m-%d} to {events['date'].max():%Y-%m-%d}")
    print(f"Single-district records: {int((events['district_scope'] == 'SINGLE_DISTRICT').sum())}")
    print(f"Multi-district records: {len(multi_events)}")
    print(f"Normalized event-date/district combinations: {len(expanded)}")
    print(f"Multiple-event dates: {len(same_date)}")
    print(f"Duration available: 0/{len(events)}")
    print(f"Severity available: {severity_available}/{len(events)}")
    print(f"Description/impact text available: {descriptions_available}/{len(events)}")
    print(f"Sources: {source_counts}")
    print(f"Analysis CSV: {ANALYSIS_PATH}")
    print(f"Design report: {REPORT_PATH}")
    print("No hourly labels, weather merges, or models were created.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError) as exc:
        print(f"FLOOD EVENT ANALYSIS FAILED: {exc}", file=sys.stderr)
        sys.exit(1)