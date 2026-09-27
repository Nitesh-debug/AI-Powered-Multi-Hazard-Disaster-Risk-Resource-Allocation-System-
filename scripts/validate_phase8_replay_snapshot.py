"""Validate the label-free Phase 8 replay artifact and its source fingerprint."""

from __future__ import annotations

import hashlib
import json
import math
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_PATH = PROJECT_ROOT / "data" / "development" / "replay_features" / "phase8_historical_replay_2025-10-31.json"
WEATHER_PATH = PROJECT_ROOT / "data" / "processed" / "weather_features.csv"
EXPECTED_DISTRICTS = {
    "Anantnag", "Bandipora", "Baramulla", "Budgam", "Doda", "Ganderbal", "Jammu", "Kathua",
    "Kishtwar", "Kulgam", "Kupwara", "Poonch", "Pulwama", "Rajouri", "Ramban", "Reasi",
    "Samba", "Shopian", "Srinagar", "Udhampur",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate() -> dict[str, object]:
    artifact = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    if artifact.get("label_scope") != "NO_LABELS_INCLUDED":
        raise ValueError("Replay artifact does not explicitly exclude label fields")
    if set(artifact.get("districts", {})) != EXPECTED_DISTRICTS:
        raise ValueError("Replay snapshot does not contain the exact 20 model districts")
    reference = date.fromisoformat(artifact["feature_reference_date"])
    target = date.fromisoformat(artifact["target_date"])
    if (target - reference).days != 1:
        raise ValueError("Replay target date is not one day after its feature reference")
    for district, record in artifact["districts"].items():
        features = record.get("features", {})
        if len(features) != 68 or any(token in name.lower() for name in features for token in ("label", "event", "disaster")):
            raise ValueError(f"Invalid feature set or label-like predictor for {district}")
        if not all(isinstance(value, (int, float)) and math.isfinite(value) for value in features.values()):
            raise ValueError(f"Replay weather inputs are not complete finite values for {district}")
        lat, lon = float(record["latitude"]), float(record["longitude"])
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError(f"Weather lookup coordinate is outside WGS84 ranges for {district}")
    if "centroid" not in artifact.get("district_coordinate_semantics", "").lower():
        raise ValueError("Coordinate semantics must state that points are not district centroids")
    recorded_hash = artifact["source"]["sha256"]
    current_hash = sha256(WEATHER_PATH)
    if recorded_hash != current_hash:
        raise ValueError("Processed weather source differs from the fingerprint used for this replay artifact")
    return artifact


def main() -> int:
    artifact = validate()
    print("PHASE 8 REPLAY SNAPSHOT VALIDATION: PASS")
    print(f"Districts: {len(artifact['districts'])}; features per district: 68")
    print(f"One-day alignment: {artifact['feature_reference_date']} -> {artifact['target_date']}")
    print("Labels included: No")
    print("Processed source fingerprint unchanged: Yes")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"PHASE 8 REPLAY SNAPSHOT VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
