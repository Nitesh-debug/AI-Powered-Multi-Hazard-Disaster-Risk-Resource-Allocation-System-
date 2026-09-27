"""Extract a label-free historical weather replay snapshot for the API demo."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.prepare_phase7_model_ready_datasets import DAILY_AGGREGATIONS, FEATURE_SCHEMA_PATH, WEATHER_PATH, deterministic_mode

TARGET_DATE = pd.Timestamp("2025-10-31")
FEATURE_REFERENCE_DATE = TARGET_DATE - pd.Timedelta(days=1)
OUTPUT_PATH = PROJECT_ROOT / "data" / "development" / "replay_features" / "phase8_historical_replay_2025-10-31.json"
EXPECTED_DISTRICTS = {
    "Anantnag", "Bandipora", "Baramulla", "Budgam", "Doda", "Ganderbal", "Jammu", "Kathua",
    "Kishtwar", "Kulgam", "Kupwara", "Poonch", "Pulwama", "Rajouri", "Ramban", "Reasi",
    "Samba", "Shopian", "Srinagar", "Udhampur",
}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def extract() -> dict[str, object]:
    schema = pd.read_csv(FEATURE_SCHEMA_PATH)
    predictors = schema.loc[schema["phase6_baseline_action"].eq("shift_by_1_day"), "source_column"].tolist()
    if len(predictors) != 68 or len(set(predictors)) != 68:
        raise ValueError("Phase 5 shifted predictor schema must contain 68 unique features")
    if set(predictors) != {*DAILY_AGGREGATIONS, "weather_code_mode"}:
        raise ValueError("Daily feature aggregations differ from the frozen Phase 5 schema")

    needed = sorted({source for source, _ in DAILY_AGGREGATIONS.values()} | {"weather_code"})
    columns = ["district", "latitude", "longitude", "time", *needed]
    slices = []
    for chunk in pd.read_csv(WEATHER_PATH, usecols=columns, chunksize=100_000, low_memory=False):
        times = pd.to_datetime(chunk["time"], errors="coerce")
        if times.isna().any():
            raise ValueError("Weather feature source contains invalid timestamps")
        mask = times.dt.normalize().eq(FEATURE_REFERENCE_DATE)
        if mask.any():
            chunk = chunk.loc[mask].copy()
            chunk["time"] = times.loc[mask]
            slices.append(chunk)
    hourly = pd.concat(slices, ignore_index=True)
    if set(hourly["district"].unique()) != EXPECTED_DISTRICTS:
        raise ValueError("Replay feature date does not cover the 20 model districts exactly")
    counts = hourly.groupby("district", sort=True).size()
    if not counts.eq(24).all() or hourly.duplicated(["district", "time"]).any():
        raise ValueError("Replay date must provide exactly 24 unique hourly rows per district")

    aggregation = {output: pd.NamedAgg(column=source, aggfunc=method) for output, (source, method) in DAILY_AGGREGATIONS.items()}
    aggregation["weather_code_mode"] = pd.NamedAgg(column="weather_code", aggfunc=deterministic_mode)
    daily = hourly.groupby("district", sort=True).agg(**aggregation)
    result: dict[str, object] = {
        "artifact_type": "historical_weather_feature_replay",
        "label_scope": "NO_LABELS_INCLUDED",
        "feature_reference_date": FEATURE_REFERENCE_DATE.strftime("%Y-%m-%d"),
        "target_date": TARGET_DATE.strftime("%Y-%m-%d"),
        "predictor_contract": "Phase 5: 68 shifted daily weather predictors; no target-date weather or label columns",
        "district_coordinate_semantics": "Weather lookup coordinates from the source file; not district centroids or administrative boundaries",
        "source": {
            "path": "data/processed/weather_features.csv",
            "sha256": file_sha256(WEATHER_PATH),
            "selection": "24 hourly rows per district on feature_reference_date, aggregated with Phase 5 daily rules",
        },
        "districts": {},
    }
    for district, row in daily.iterrows():
        coordinates = hourly.loc[hourly["district"].eq(district), ["latitude", "longitude"]].drop_duplicates()
        if len(coordinates) != 1:
            raise ValueError(f"Weather coordinate is not unique for {district}")
        values = {name: (None if pd.isna(row[name]) else float(row[name])) for name in predictors}
        if any(value is None for value in values.values()):
            raise ValueError(f"Replay weather feature row has unavailable values for {district}")
        result["districts"][district] = {
            "latitude": float(coordinates.iloc[0]["latitude"]),
            "longitude": float(coordinates.iloc[0]["longitude"]),
            "features": values,
        }
    return result


def main() -> int:
    artifact = extract()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT_PATH.with_name(f".{OUTPUT_PATH.name}.tmp")
    temporary.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(OUTPUT_PATH)
    print("PHASE 8 REPLAY SNAPSHOT: PASS")
    print(f"Districts: {len(artifact['districts'])}")
    print("Feature rows: 20 x 68; label columns: none")
    print(f"Alignment: {artifact['feature_reference_date']} -> {artifact['target_date']}")
    print(f"Artifact: {OUTPUT_PATH.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"PHASE 8 REPLAY SNAPSHOT FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
