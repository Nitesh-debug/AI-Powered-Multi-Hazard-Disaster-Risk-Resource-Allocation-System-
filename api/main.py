from __future__ import annotations

import hashlib
import json
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import joblib
import numpy as np
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from api.config import APP_TIMEZONE, CORS_ORIGINS, MAX_REQUEST_BODY_BYTES, MODEL_ROOT, MODEL_VERSION, REPLAY_PATH, RULE_VERSION, SYNTHETIC_SCOPE
from api.resource_planning import SIMULATION_DISCLAIMER, build_response_plan
from api.resources import exposure_for_district, load_scenario, resources_for_district
from api.schemas import AllocationRequest, PredictionRequest
from api.store import DemoStore, SupabaseMirror, utc_now
from api.weather import OpenMeteoFeatureProvider, SimulatedDemoWeatherProvider, WeatherFeatureProvider, replay_features

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger("jk-disaster-api")
HAZARDS = ("flood", "heavy_rain", "landslide", "heatwave", "coldwave", "windstorm")
EXPECTED_DISTRICTS = (
    "Anantnag", "Bandipora", "Baramulla", "Budgam", "Doda", "Ganderbal", "Jammu", "Kathua",
    "Kishtwar", "Kulgam", "Kupwara", "Poonch", "Pulwama", "Rajouri", "Ramban", "Reasi",
    "Samba", "Shopian", "Srinagar", "Udhampur",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class ModelRegistry:
    def __init__(self):
        self.models: dict[str, dict[str, Any]] = {}
        for hazard in HAZARDS:
            directory = MODEL_ROOT / hazard
            metadata_path = directory / "metadata.json"
            model_path = directory / "model.joblib"
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            if metadata.get("label_scope") != SYNTHETIC_SCOPE or metadata.get("model_version") != MODEL_VERSION:
                raise RuntimeError(f"Model registry refused non-development or incompatible artifact for {hazard}")
            if metadata.get("model_sha256") != sha256(model_path):
                raise RuntimeError(f"Model integrity check failed for {hazard}")
            if (
                metadata.get("label_version") != RULE_VERSION
                or metadata.get("feature_schema_version") != "phase5_68_shifted_weather_v1"
                or len(metadata.get("feature_columns", [])) != 68
                or metadata.get("test_metrics") is None
                or metadata.get("test_data_accessed") is not True
                or metadata.get("test_evaluation", {}).get("status") != "completed_once"
                or metadata.get("calibration", {}).get("calibrated") is not False
                or "SYNTHETIC_DEVELOPMENT_ONLY" not in metadata.get("label_warning", "")
            ):
                raise RuntimeError(f"Model selection/final evaluation is incomplete for {hazard}")
            self.models[hazard] = {"estimator": joblib.load(model_path), "metadata": metadata}

    def predict(self, features: dict[str, float]) -> list[dict[str, Any]]:
        result = []
        for hazard in HAZARDS:
            item = self.models[hazard]
            metadata = item["metadata"]
            names = metadata["feature_columns"]
            if set(names) != set(features) or len(names) != 68:
                raise ValueError(f"Feature schema mismatch for {hazard}")
            vector = np.asarray([[features[name] for name in names]], dtype=np.float32)
            estimator = item["estimator"]
            positive_index = np.flatnonzero(estimator.classes_ == 1)
            if len(positive_index) != 1:
                raise ValueError(f"Model does not expose one positive class for {hazard}")
            score = float(estimator.predict_proba(vector)[0, int(positive_index[0])])
            threshold = float(metadata["threshold_selection"]["selected_threshold"])
            result.append({
                "hazard": hazard,
                "raw_model_score": score,
                "raw_model_score_pct_for_display": round(score * 100, 4),
                "development_score_pct": round(score * 100, 4),
                "validation_threshold_score": threshold,
                "validation_threshold_pct": round(threshold * 100, 4),
                "above_validation_threshold": bool(score >= threshold),
                "calibrated_probability": False,
                "score_semantics": "raw uncalibrated estimator score; percentage is display scaling, not probability",
                "label_scope": SYNTHETIC_SCOPE,
                "model_version": MODEL_VERSION,
            })
        return result


def make_services() -> tuple[dict[str, Any], DemoStore, SupabaseMirror, WeatherFeatureProvider, SimulatedDemoWeatherProvider, dict[str, Any]]:
    artifact = json.loads(REPLAY_PATH.read_text(encoding="utf-8"))
    if artifact.get("label_scope") != "NO_LABELS_INCLUDED" or set(artifact.get("districts", {})) != set(EXPECTED_DISTRICTS):
        raise RuntimeError("Historical replay feature artifact failed its scope/district checks")
    mirror = SupabaseMirror()
    mirror.check_schema()
    scenario = load_scenario()
    return artifact, DemoStore(), mirror, OpenMeteoFeatureProvider(), SimulatedDemoWeatherProvider(), scenario


class RequestBodyLimitMiddleware:
    def __init__(self, app, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        declared_size = next((value.decode("latin-1") for name, value in scope.get("headers", []) if name == b"content-length"), None)
        if declared_size:
            try:
                if int(declared_size) > self.max_bytes:
                    await self._reject(send, 413, "Request body exceeds the configured size limit")
                    return
            except ValueError:
                await self._reject(send, 400, "Invalid Content-Length header")
                return
        body = bytearray()
        more_body = True
        while more_body:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            if message["type"] == "http.request":
                body.extend(message.get("body", b""))
                if len(body) > self.max_bytes:
                    await self._reject(send, 413, "Request body exceeds the configured size limit")
                    return
                more_body = message.get("more_body", False)
        delivered = False

        async def replay_body():
            nonlocal delivered
            if delivered:
                return {"type": "http.request", "body": b"", "more_body": False}
            delivered = True
            return {"type": "http.request", "body": bytes(body), "more_body": False}

        await self.app(scope, replay_body, send)

    @staticmethod
    async def _reject(send, status_code: int, detail: str) -> None:
        body = json.dumps({"detail": detail}).encode("utf-8")
        await send({"type": "http.response.start", "status": status_code, "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode("ascii"))]})
        await send({"type": "http.response.body", "body": body})


app = FastAPI(title="JK Disaster Development System", version="0.1.0", description="SYNTHETIC_DEVELOPMENT_ONLY research and workflow demo")
app.add_middleware(RequestBodyLimitMiddleware, max_bytes=MAX_REQUEST_BODY_BYTES)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(CORS_ORIGINS),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


try:
    REPLAY, STORE, SUPABASE, WEATHER, DEMO_WEATHER, SCENARIO = make_services()
    MODELS = ModelRegistry()
    STARTUP_ERROR = ""
except Exception as exc:  # Keep health endpoint available for a useful setup error.
    LOGGER.exception("Service initialization failed")
    REPLAY, STORE, SUPABASE, WEATHER, DEMO_WEATHER, SCENARIO, MODELS = {}, None, SupabaseMirror(), OpenMeteoFeatureProvider(), None, {}, None
    STARTUP_ERROR = f"Service initialization failed: {type(exc).__name__}"


def require_services() -> None:
    if STARTUP_ERROR or STORE is None or MODELS is None:
        raise HTTPException(status_code=503, detail=STARTUP_ERROR or "Service is not ready")


def district_reference(district: str) -> dict[str, float]:
    entry = REPLAY["districts"].get(district)
    if entry is None:
        raise HTTPException(status_code=404, detail="Unknown model district")
    return {"latitude": float(entry["latitude"]), "longitude": float(entry["longitude"])}


def evaluate_district(district: str, mode: str) -> dict[str, Any]:
    reference = district_reference(district)
    try:
        if mode == "historical_replay":
            source_data = replay_features(REPLAY, district)
        elif mode == "simulated_demo":
            source_data = DEMO_WEATHER.fetch_features(district, **reference)
        else:
            source_data = WEATHER.fetch_features(district, **reference)
        hazards = MODELS.predict(source_data["features"])
        for item in hazards:
            item.update({
                "district": district,
                "feature_reference_date": source_data["feature_reference_date"],
                "target_date": source_data["target_date"],
            })
        active_signals = [item["hazard"] for item in hazards if item["above_validation_threshold"]]
        return {
            "district": district,
            "status": "complete",
            "feature_reference_date": source_data["feature_reference_date"],
            "target_date": source_data["target_date"],
            "coordinates": reference,
            "source": source_data["source"],
            "weather_scope": source_data.get("weather_scope", "OBSERVED_LIVE_WEATHER" if mode == "live" else "OBSERVED_HISTORICAL_WEATHER_FEATURES"),
            "retrieved_at": source_data.get("retrieved_at"),
            "fixture_version": source_data.get("fixture_version"),
            "provider_grid": source_data["provider_grid"],
            "weather_summary": source_data["weather_summary"],
            "hazards": hazards,
            "active_hazard_signals": active_signals,
            "combined_development_risk_score": max(item["raw_model_score"] for item in hazards),
            "combined_risk_method": "maximum raw hazard score; no weights; uncalibrated synthetic-development scores",
            "model_version": MODEL_VERSION,
            "label_scope": SYNTHETIC_SCOPE,
        }
    except Exception as exc:
        LOGGER.warning("District assessment unavailable for %s (%s)", district, type(exc).__name__)
        return {
            "district": district,
            "status": "unavailable",
            "coordinates": reference,
            "reason": str(exc),
            "hazards": [],
            "active_hazard_signals": [],
            "combined_development_risk_score": None,
            "model_version": MODEL_VERSION,
            "label_scope": SYNTHETIC_SCOPE,
            "weather_scope": "UNAVAILABLE",
        }


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "status": "ready" if not STARTUP_ERROR else "degraded",
        "scope": SYNTHETIC_SCOPE,
        "models_loaded": len(MODELS.models) if MODELS else 0,
        "model_version": MODEL_VERSION,
        "label_rule_version": RULE_VERSION,
        "live_weather_provider": "Open-Meteo ECMWF adapter; Srinagar smoke-tested only; no API key configured",
        "supabase": SUPABASE.status if SUPABASE else "not configured; SQLite active",
        "persistence": "SQLite active; Supabase optional server-side mirror",
        "simulation_version": SCENARIO.get("simulation_version") if SCENARIO else None,
        "demo_weather_fixture": DEMO_WEATHER.fixture.get("fixture_version") if DEMO_WEATHER else None,
        "outbound_notifications": "disabled for synthetic development outputs",
        "startup_error": STARTUP_ERROR or None,
    }


@app.get("/api/districts")
def districts() -> dict[str, Any]:
    if not REPLAY:
        raise HTTPException(status_code=503, detail=STARTUP_ERROR)
    return {"districts": [
        {"name": district, "latitude": REPLAY["districts"][district]["latitude"], "longitude": REPLAY["districts"][district]["longitude"],
         "coordinate_type": "weather reference point; not boundary or centroid"}
        for district in EXPECTED_DISTRICTS
    ]}


@app.get("/api/resources")
def list_resources(district: str | None = Query(default=None)) -> dict[str, Any]:
    require_services()
    if district is not None and district not in SCENARIO["district_order"]:
        raise HTTPException(status_code=404, detail="Unknown model district")
    records = resources_for_district(SCENARIO, district)
    return {
        "simulation_version": SCENARIO["simulation_version"],
        "data_scope": "SIMULATED_DEVELOPMENT_ONLY",
        "operational_status": SIMULATION_DISCLAIMER,
        "count": len(records),
        "resources": records,
    }


@app.get("/api/resources/{resource_id}")
def get_resource(resource_id: str) -> dict[str, Any]:
    require_services()
    record = next((item for item in SCENARIO["resources"] if item["resource_id"] == resource_id), None)
    if record is None:
        raise HTTPException(status_code=404, detail="Simulated resource not found")
    return {**record, "operational_status": SIMULATION_DISCLAIMER}


@app.get("/api/exposure")
def get_exposure(district: str | None = Query(default=None)) -> dict[str, Any]:
    require_services()
    if district is not None and district not in SCENARIO["district_order"]:
        raise HTTPException(status_code=404, detail="Unknown model district")
    records = exposure_for_district(SCENARIO, district)
    return {
        "simulation_version": SCENARIO["simulation_version"],
        "data_scope": "SIMULATED_DEVELOPMENT_ONLY",
        "operational_status": SIMULATION_DISCLAIMER,
        "count": len(records),
        "districts": records,
    }


@app.get("/api/registry")
def registry() -> dict[str, Any]:
    require_services()
    return {"scope": SYNTHETIC_SCOPE, "hazards": [
        {"hazard": hazard, "algorithm": MODELS.models[hazard]["metadata"]["selected_algorithm"],
         "model_version": MODEL_VERSION, "label_version": RULE_VERSION,
         "selected_candidate_id": MODELS.models[hazard]["metadata"]["selected_candidate_id"],
         "validation_ap": MODELS.models[hazard]["metadata"]["validation_metrics_at_0_5"]["validation_average_precision"],
         "test_ap": MODELS.models[hazard]["metadata"]["test_metrics"]["average_precision"],
         "score_semantics": "raw uncalibrated estimator score; not a calibrated probability",
         "label_scope": SYNTHETIC_SCOPE}
        for hazard in HAZARDS
    ]}


@app.post("/api/predictions")
def predictions(request: PredictionRequest) -> dict[str, Any]:
    require_services()
    results = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(evaluate_district, district, request.mode): district for district in EXPECTED_DISTRICTS}
        for future in as_completed(futures):
            district = futures[future]
            try:
                results.append(future.result())
            except Exception as exc:
                LOGGER.warning("District worker failed for %s (%s)", district, type(exc).__name__)
                results.append({"district": district, "status": "unavailable", "reason": "District assessment failed; other district results are retained.", "hazards": [], "active_hazard_signals": [], "combined_development_risk_score": None, "model_version": MODEL_VERSION, "label_scope": SYNTHETIC_SCOPE, "weather_scope": "UNAVAILABLE"})
    results.sort(key=lambda row: EXPECTED_DISTRICTS.index(row["district"]))
    completed = [row for row in results if row["status"] == "complete"]
    date_counts: dict[tuple[str, str], int] = {}
    for row in completed:
        key = (row["feature_reference_date"], row["target_date"])
        date_counts[key] = date_counts.get(key, 0) + 1
    if date_counts:
        first_seen = {key: next(i for i, row in enumerate(completed) if (row["feature_reference_date"], row["target_date"]) == key) for key in date_counts}
        canonical_dates = max(date_counts, key=lambda key: (date_counts[key], -first_seen[key]))
        for row in completed:
            if (row["feature_reference_date"], row["target_date"]) != canonical_dates:
                row.update({"status": "unavailable", "reason": "Provider returned dates inconsistent with the district cohort; result excluded.", "hazards": [], "active_hazard_signals": [], "combined_development_risk_score": None, "weather_scope": "UNAVAILABLE"})
        completed = [row for row in results if row["status"] == "complete"]
    if completed:
        feature_reference_date, target_date = completed[0]["feature_reference_date"], completed[0]["target_date"]
    elif request.mode == "historical_replay":
        feature_reference_date, target_date = REPLAY["feature_reference_date"], REPLAY["target_date"]
    elif request.mode == "simulated_demo":
        feature_reference_date, target_date = DEMO_WEATHER.fixture["feature_reference_date"], DEMO_WEATHER.fixture["target_date"]
    else:
        today = datetime.now(ZoneInfo(APP_TIMEZONE)).date()
        feature_reference_date, target_date = (today - timedelta(days=1)).isoformat(), today.isoformat()
    source_name = {"historical_replay": "historical replay weather features", "live": "Open-Meteo ECMWF hourly API", "simulated_demo": "SIMULATED_DEMO_WEATHER fixture"}[request.mode]
    created_at = utc_now()
    for result in completed:
        for hazard in result["hazards"]:
            score, threshold = float(hazard["raw_model_score"]), float(hazard["validation_threshold_score"])
            ratio = score / threshold if threshold > 0 else float("inf")
            level = "NORMAL" if score < threshold else "HIGH" if ratio >= 2 else "ELEVATED" if ratio >= 1.5 else "WATCH"
            hazard.update({
                "alert_level": level,
                "alert_timestamp": created_at,
                "alert_district": result["district"],
                "alert_model_version": MODEL_VERSION,
                "alert_reason": f"Raw uncalibrated synthetic score {score:.4f} {'exceeded' if score >= threshold else 'did not exceed'} validation threshold {threshold:.4f}.",
                "alert_data_source": result["source"],
                "alert_status": "DEVELOPMENT_SIMULATION_NOT_A_GOVERNMENT_WARNING",
            })
    retrieved = [row.get("retrieved_at") for row in completed if row.get("retrieved_at")]
    if request.mode == "live":
        freshness = {"status": "live provider response; per-district fetch timestamp", "retrieved_at": max(retrieved) if retrieved else None, "source": source_name}
    elif request.mode == "simulated_demo":
        freshness = {"status": "fixed synthetic fixture; not current weather", "retrieved_at": None, "source": source_name, "fixture_version": DEMO_WEATHER.fixture["fixture_version"]}
    else:
        freshness = {"status": "fixed historical snapshot", "retrieved_at": None, "source": source_name, "data_as_of": target_date}
    run = {
        "id": str(uuid.uuid4()),
        "mode": request.mode,
        "source": source_name,
        "feature_reference_date": feature_reference_date,
        "target_date": target_date,
        "created_at": created_at,
        "data_freshness": freshness,
        "label_scope": SYNTHETIC_SCOPE,
        "label_rule_version": RULE_VERSION,
        "model_version": MODEL_VERSION,
        "combined_risk_method": "maximum raw hazard score per district; no weights; synthetic and uncalibrated",
        "status": "complete" if len(completed) == len(EXPECTED_DISTRICTS) else "partial" if completed else "unavailable",
        "district_count": len(completed),
        "unavailable_district_count": len(results) - len(completed),
        "district_results": results,
        "operational_use": "PROHIBITED: synthetic development labels and uncalibrated scores",
    }
    STORE.save_prediction_run(run, results)
    if SUPABASE.enabled:
        mirror_ok = True
        try:
            SUPABASE.mirror("prediction_runs", {
                "id": run["id"], "mode": run["mode"], "source": run["source"],
                "feature_reference_date": run["feature_reference_date"], "target_date": run["target_date"],
                "label_scope": run["label_scope"], "created_at": run["created_at"], "payload": run,
            })
        except Exception as exc:
            mirror_ok = False
            LOGGER.warning("Supabase prediction mirror failed: %s", type(exc).__name__)
        for district_result in results:
            for hazard in district_result.get("hazards", []):
                if not hazard["above_validation_threshold"]:
                    continue
                alert = {
                    "id": f"{run['id']}:{district_result['district']}:{hazard['hazard']}",
                    "run_id": run["id"], "district": district_result["district"], "hazard": hazard["hazard"],
                    "score": hazard["raw_model_score"], "threshold": hazard["validation_threshold_score"],
                    "raw_model_score": hazard["raw_model_score"],
                    "validation_threshold_score": hazard["validation_threshold_score"],
                    "score_semantics": hazard["score_semantics"],
                    "status": "DEVELOPMENT_SIGNAL_NOT_FOR_DISPATCH", "label_scope": SYNTHETIC_SCOPE,
                    "created_at": run["created_at"], "payload": hazard,
                }
                try:
                    SUPABASE.mirror("development_alerts", alert)
                except Exception as exc:
                    mirror_ok = False
                    LOGGER.warning("Supabase alert mirror failed: %s", type(exc).__name__)
        run["supabase_mirror"] = "synced" if mirror_ok else "partial/failed; SQLite copy retained"
    return run


@app.get("/api/response-plan")
def response_plan(run_id: str | None = Query(default=None)) -> dict[str, Any]:
    require_services()
    if run_id is None:
        recent_runs = STORE.recent("prediction_runs", 1)
        run = recent_runs[0] if recent_runs else None
    else:
        run = STORE.get_prediction_run(run_id)
    if run is None:
        return {"status": "no_prediction_run", "simulation_version": SCENARIO["simulation_version"], "operational_status": SIMULATION_DISCLAIMER, "recommendations": [], "allocations": []}
    return build_response_plan(run, SCENARIO)


def simulate_allocation_for_run(run: dict[str, Any]) -> dict[str, Any]:
    result = build_response_plan(run, SCENARIO)
    result.update({
        "id": str(uuid.uuid4()),
        "prediction_run_id": run["id"],
        "created_at": utc_now(),
        "label_scope": SYNTHETIC_SCOPE,
        "production_input_availability": {
            "population_or_exposure": {"status": "unavailable", "source": None},
            "vulnerability": {"status": "unavailable", "source": None},
            "resource_suitability": {"status": "unavailable", "source": None},
            "real_resource_availability": {"status": "unavailable", "source": None},
            "distance_or_travel_time": {"status": "unavailable", "source": None},
            "capacity_constraints": {"status": "unavailable", "source": None},
        },
        "operational_disclaimer": SIMULATION_DISCLAIMER,
        "status": "SIMULATION_ONLY_NOT_FOR_DISPATCH",
    })
    for allocation in result["allocations"]:
        allocation["simulation_priority"] = allocation["priority_score"]
        allocation["development_signals"] = allocation["hazards"]
        allocation["raw_model_score"] = allocation["risk_score"]
    STORE.save_allocation(result)
    if SUPABASE.enabled:
        try:
            SUPABASE.mirror("allocation_runs", {
                "id": result["id"], "prediction_run_id": result["prediction_run_id"],
                "inventory_scope": result["inventory"]["scope"], "created_at": result["created_at"],
                "payload": result,
            })
        except Exception as exc:
            LOGGER.warning("Supabase allocation mirror failed: %s", type(exc).__name__)
    return result


@app.post("/api/allocations")
@app.post("/api/allocations/simulate")
def allocations(request: AllocationRequest) -> dict[str, Any]:
    require_services()
    run = STORE.get_prediction_run(request.run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Prediction run not found")
    return simulate_allocation_for_run(run)


@app.get("/api/alerts")
def alerts(limit: int = Query(default=50, ge=1, le=200)) -> dict[str, Any]:
    require_services()
    return {"scope": SYNTHETIC_SCOPE, "notification_status": "disabled", "alerts": STORE.recent("development_alerts", limit)}


@app.get("/api/runs")
def runs(limit: int = Query(default=20, ge=1, le=100)) -> dict[str, Any]:
    require_services()
    return {"runs": STORE.recent("prediction_runs", limit)}
