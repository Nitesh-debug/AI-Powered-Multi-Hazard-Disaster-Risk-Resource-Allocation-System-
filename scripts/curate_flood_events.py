"""Curate IFI flood records using only the source's own wording."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = PROJECT_ROOT / "data" / "raw" / "disasters" / "flood_inventory.csv"
OUTPUT_PATH = PROJECT_ROOT / "data" / "raw" / "disasters" / "curated_flood_events.csv"
REPORT_PATH = PROJECT_ROOT / "results" / "flood_curation_report.csv"
PROJECT_DISTRICTS = {
    "Jammu", "Srinagar", "Anantnag", "Baramulla", "Kupwara", "Pulwama",
    "Budgam", "Bandipora", "Ganderbal", "Doda", "Kathua", "Udhampur",
    "Rajouri", "Poonch", "Kulgam", "Kishtwar", "Ramban", "Reasi",
    "Samba", "Shopian",
}

ALLOWED_STATUSES = {"EXPLICIT_FLOOD", "AMBIGUOUS", "NOT_FLOOD"}
FLOOD_TERMS = re.compile(r"\bflood(?:s|ing|ed)?\b|\binundat(?:e|ed|ion)\b", re.IGNORECASE)
NON_FLOOD_TERMS = re.compile(r"\blandslide\b|\bmudslide\b|\bmassive landslide\b", re.IGNORECASE)


def source_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def district_tokens(values: pd.Series) -> set[str]:
    return {
        token.strip()
        for value in values
        for token in source_text(value).split(",")
        if token.strip()
    }


def classify_record(cause: str, description: str) -> tuple[str, str]:
    wording = " ".join(part for part in (cause, description) if part).strip()
    if FLOOD_TERMS.search(wording):
        return "EXPLICIT_FLOOD", "Source wording explicitly contains flood, flash flood, flooding, or inundation terminology."
    if NON_FLOOD_TERMS.search(wording):
        return "NOT_FLOOD", "Source wording documents landslide or mudslide without explicit flood/inundation wording."
    if wording:
        return "AMBIGUOUS", "Source mentions rain, heavy rain, or cloudburst without explicit flood/inundation wording."
    return "AMBIGUOUS", "Source provides no usable hazard wording for a flood classification."


def main() -> int:
    source = pd.read_csv(INPUT_PATH)
    if len(source) != 77:
        raise ValueError(f"Expected 77 IFI records, found {len(source)}")

    descriptions = source.apply(
        lambda row: " | ".join(
            value
            for value in (
                source_text(row["Description of Casualties/injured"]),
                source_text(row["Extent of damage "]),
            )
            if value
        ),
        axis=1,
    )
    classifications = [
        classify_record(source_text(row["Main Cause"]), description)
        for (_, row), description in zip(source.iterrows(), descriptions)
    ]

    curated = pd.DataFrame(
        {
            "event_id": source["UEI"].astype(str),
            "date": pd.to_datetime(source["Start Date"], dayfirst=True, errors="coerce").dt.strftime("%Y-%m-%d"),
            "district": source["Districts"].map(source_text),
            "original_description": descriptions,
            "original_cause": source["Main Cause"].map(source_text),
            "severity": source["Severity"],
            "source": source["Event Source"].map(source_text),
            "source_url": source["source_url"].map(source_text),
            "lgd_code": source["District_LGD_Codes"],
            "flood_label_status": [item[0] for item in classifications],
            "curation_reason": [item[1] for item in classifications],
        }
    )
    if not set(curated["flood_label_status"]).issubset(ALLOWED_STATUSES):
        raise ValueError("Unexpected curation status generated")
    if curated["event_id"].duplicated().any():
        raise ValueError("Duplicate event IDs found")

    curated = curated.sort_values(["date", "district", "original_cause"], na_position="last").reset_index(drop=True)
    counts = curated["flood_label_status"].value_counts().reindex(sorted(ALLOWED_STATUSES), fill_value=0)
    represented_tokens = district_tokens(curated["district"])
    report = pd.DataFrame(
        {
            "classification": counts.index,
            "count": counts.values,
        }
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    curated.to_csv(OUTPUT_PATH, index=False, encoding="utf-8")
    report.to_csv(REPORT_PATH, index=False, encoding="utf-8")

    print("=" * 72)
    print("IFI FLOOD EVENT CURATION")
    print("=" * 72)
    print(f"Total records: {len(curated)}")
    print(f"EXPLICIT_FLOOD records: {int(counts['EXPLICIT_FLOOD'])}")
    print(f"AMBIGUOUS records: {int(counts['AMBIGUOUS'])}")
    print(f"NOT_FLOOD records: {int(counts['NOT_FLOOD'])}")
    print(f"District field values represented: {curated['district'].replace('', pd.NA).dropna().nunique()}")
    print(f"Unique district tokens represented: {len(represented_tokens)}")
    print(f"Project districts represented: {', '.join(sorted(represented_tokens & PROJECT_DISTRICTS))}")
    print(f"Project districts missing: {', '.join(sorted(PROJECT_DISTRICTS - represented_tokens)) or 'None'}")
    print(f"Date range: {curated['date'].min()} to {curated['date'].max()}")
    print("Events per district:")
    print(curated["district"].replace("", pd.NA).dropna().value_counts().sort_index().to_string())
    print("Events per year:")
    print(pd.to_datetime(curated["date"]).dt.year.value_counts().sort_index().to_string())
    print("Examples by classification:")
    for status in ("EXPLICIT_FLOOD", "AMBIGUOUS", "NOT_FLOOD"):
        print(f"  {status}:")
        examples = curated[curated["flood_label_status"] == status].head(3)
        for _, row in examples.iterrows():
            print(f"    {row['event_id']} | {row['date']} | {row['district']} | cause={row['original_cause']!r} | description={row['original_description']!r}")
    print(f"Curated output: {OUTPUT_PATH}")
    print(f"Curation report: {REPORT_PATH}")
    print("No weather data, hourly labels, or ML models were created.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError) as exc:
        print(f"FLOOD CURATION FAILED: {exc}", file=sys.stderr)
        sys.exit(1)