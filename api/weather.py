from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Protocol
from zoneinfo import ZoneInfo

import httpx
import numpy as np
import pandas as pd

from api.config import APP_TIMEZONE, DEMO_WEATHER_PATH, OPEN_METEO_URL, WEATHER_TIMEOUT_SECONDS
from scripts.build_weather_features import create_features
from scripts.prepare_phase7_model_ready_datasets import DAILY_AGGREGATIONS

HOURLY_VARIABLES = [
    "temperature_2m", "relative_humidity_2m", "precipitation", "rain", "snowfall", "snow_depth",
    "weather_code", "wind_speed_10m", "wind_gusts_10m", "soil_temperature_0_to_7cm",
    "soil_temperature_7_to_28cm", "soil_temperature_28_to_100cm", "soil_moisture_0_to_7cm",
    "soil_moisture_7_to_28cm", "soil_moisture_28_to_100cm",
]


class WeatherUnavailable(RuntimeError):
    pass


class WeatherFeatureProvider(Protocol):
    def fetch_features(self, district: str, latitude: float, longitude: float) -> dict[str, Any]: ...


class OpenMeteoFeatureProvider:
    def __init__(self, *, base_url: str = OPEN_METEO_URL, timeout: float = WEATHER_TIMEOUT_SECONDS, transport: httpx.BaseTransport | None = None):
        self.base_url = base_url
        self.timeout = timeout
        self.transport = transport

    def fetch_features(self, district: str, latitude: float, longitude: float) -> dict[str, Any]:
        yesterday = (datetime.now(ZoneInfo(APP_TIMEZONE)).date() - timedelta(days=1)).isoformat()
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": ",".join(HOURLY_VARIABLES),
            "past_days": 7,
            "forecast_days": 1,
            "timezone": APP_TIMEZONE,
            "temperature_unit": "celsius",
            "wind_speed_unit": "kmh",
            "precipitation_unit": "mm",
        }
        try:
            with httpx.Client(timeout=self.timeout, transport=self.transport) as client:
                response = client.get(self.base_url, params=params)
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise WeatherUnavailable("Open-Meteo request failed; no live prediction was produced") from exc

        hourly = payload.get("hourly") or {}
        missing = [name for name in ["time", *HOURLY_VARIABLES] if name not in hourly]
        if missing:
            raise WeatherUnavailable(f"Open-Meteo response is missing required fields: {', '.join(missing)}")
        sizes = {len(hourly[name]) for name in ["time", *HOURLY_VARIABLES]}
        if len(sizes) != 1:
            raise WeatherUnavailable("Open-Meteo response has inconsistent hourly array lengths")
        try:
            frame = pd.DataFrame({name: hourly[name] for name in ["time", *HOURLY_VARIABLES]})
            frame["time"] = pd.to_datetime(frame["time"], errors="coerce")
            for name in HOURLY_VARIABLES:
                frame[name] = pd.to_numeric(frame[name], errors="coerce")
        except (TypeError, ValueError) as exc:
            raise WeatherUnavailable("Open-Meteo response could not be parsed") from exc
        if frame.empty or frame["time"].isna().any() or frame[HOURLY_VARIABLES].isna().any().any():
            raise WeatherUnavailable("Required weather inputs are unavailable; missing values are not imputed")
        frame = frame.sort_values("time", kind="stable").reset_index(drop=True)
        if frame["time"].duplicated().any() or not frame["time"].diff().dropna().eq(pd.Timedelta(hours=1)).all():
            raise WeatherUnavailable("Hourly provider series is incomplete or has duplicate timestamps")

        reference_date = pd.Timestamp(yesterday)
        selected = frame.loc[frame["time"].dt.normalize().eq(reference_date)].copy()
        if len(selected) != 24 or selected["time"].dt.hour.tolist() != list(range(24)):
            raise WeatherUnavailable(f"A complete UTC weather day for {yesterday} is not available")

        # Build rolling inputs only through the selected feature-reference date.
        available = frame.loc[frame["time"].le(reference_date + pd.Timedelta(hours=23))].copy()
        available["district"] = district
        create_features(available)
        day = available.loc[available["time"].dt.normalize().eq(reference_date)]
        if len(day) != 24:
            raise WeatherUnavailable("Feature-reference day became incomplete during feature engineering")
        aggregations = {output: (source, operation) for output, (source, operation) in DAILY_AGGREGATIONS.items()}
        values: dict[str, float] = {}
        for output, (source, operation) in aggregations.items():
            series = day[source]
            values[output] = float(series.iloc[-1] if operation == "last" else getattr(series, operation)())
        modes = day["weather_code"].mode(dropna=True)
        if modes.empty:
            raise WeatherUnavailable("Weather-code feature is unavailable")
        values["weather_code_mode"] = float(modes.iloc[0])
        if len(values) != 68 or not np.isfinite(np.asarray(list(values.values()), dtype=np.float64)).all():
            raise WeatherUnavailable("Engineered live features do not satisfy the complete 68-feature contract")
        return {
            "district": district,
            "feature_reference_date": yesterday,
            "target_date": (reference_date + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
            "source": "Open-Meteo ECMWF hourly API",
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "timezone": APP_TIMEZONE,
            "features": values,
            "weather_summary": {
                "temperature_mean_c": values["temperature_2m_daily_mean"],
                "precipitation_total_mm": values["precipitation_daily_sum"],
                "wind_speed_mean_kmh": values["wind_speed_10m_daily_mean"],
                "weather_code": values["weather_code_mode"],
            },
            "provider_grid": {
                "latitude": payload.get("latitude"),
                "longitude": payload.get("longitude"),
                "elevation_m": payload.get("elevation"),
            },
        }


class SimulatedDemoWeatherProvider:
    def __init__(self, fixture_path: Path = DEMO_WEATHER_PATH):
        self.fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        if (
            self.fixture.get("weather_scope") != "SIMULATED_DEMO_WEATHER"
            or self.fixture.get("feature_schema_version") != "phase5_68_shifted_weather_v1"
            or len(self.fixture.get("districts", {})) != 20
        ):
            raise RuntimeError("Offline demo weather fixture failed scope/schema/district checks")

    def fetch_features(self, district: str, latitude: float, longitude: float) -> dict[str, Any]:
        record = self.fixture["districts"].get(district)
        if record is None:
            raise WeatherUnavailable(f"No simulated demo weather fixture exists for {district}")
        features = record["features"]
        if len(features) != 68 or not np.isfinite(np.asarray(list(features.values()), dtype=np.float64)).all():
            raise WeatherUnavailable(f"Simulated demo weather feature contract failed for {district}")
        return {
            "district": district,
            "feature_reference_date": self.fixture["feature_reference_date"],
            "target_date": self.fixture["target_date"],
            "source": "SIMULATED_DEMO_WEATHER",
            "weather_scope": "SIMULATED_DEMO_WEATHER",
            "fixture_version": self.fixture["fixture_version"],
            "retrieved_at": None,
            "features": features,
            "weather_summary": {
                "temperature_mean_c": features["temperature_2m_daily_mean"],
                "precipitation_total_mm": features["precipitation_daily_sum"],
                "wind_speed_mean_kmh": features["wind_speed_10m_daily_mean"],
                "weather_code": features["weather_code_mode"],
            },
            "provider_grid": {"latitude": record["latitude"], "longitude": record["longitude"], "elevation_m": None},
        }


def replay_features(artifact: dict[str, Any], district: str) -> dict[str, Any]:
    record = artifact["districts"].get(district)
    if record is None:
        raise WeatherUnavailable(f"No historical replay feature row exists for {district}")
    values = record["features"]
    return {
        "district": district,
        "feature_reference_date": artifact["feature_reference_date"],
        "target_date": artifact["target_date"],
        "source": "historical replay from processed weather feature source",
        "weather_scope": "OBSERVED_HISTORICAL_WEATHER_FEATURES",
        "retrieved_at": None,
        "features": values,
        "weather_summary": {
            "temperature_mean_c": values["temperature_2m_daily_mean"],
            "precipitation_total_mm": values["precipitation_daily_sum"],
            "wind_speed_mean_kmh": values["wind_speed_10m_daily_mean"],
            "weather_code": values["weather_code_mode"],
        },
        "provider_grid": {"latitude": record["latitude"], "longitude": record["longitude"], "elevation_m": None},
    }
