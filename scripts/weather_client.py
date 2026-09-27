"""
Weather ingestion with live API hooks and an offline dummy fallback.

Swap providers by setting WEATHER_PROVIDER:
  auto | openweather | imd | openmeteo | dummy
"""

from __future__ import annotations

import datetime as dt
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import pandas as pd
import requests

from scripts.settings import WeatherConfig, weather_config
from scripts.district_info import district_data


def dummy_weather_frame(seed: int | None = 42) -> pd.DataFrame:
    """Offline synthetic observations used when live APIs are unavailable."""
    rng = random.Random(seed)
    records: list[dict[str, Any]] = []
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    for district in district_data:
        records.append(
            {
                "District": district,
                "Fetch_Time_UTC": now,
                "Temp_C": round(rng.uniform(5, 32), 2),
                "Humidity": round(rng.uniform(30, 90), 2),
                "Wind_Kph": round(rng.uniform(2, 40), 2),
                "Pressure_mb": round(rng.uniform(990, 1022), 2),
                "Precip_mm": round(rng.uniform(0, 12), 2),
                "source": "dummy",
            }
        )
    return pd.DataFrame(records)


def _normalize_record(district: str, temp: float, humidity: float, wind_kph: float, pressure: float, precip: float, source: str) -> dict[str, Any]:
    return {
        "District": district,
        "Fetch_Time_UTC": dt.datetime.now(dt.timezone.utc).isoformat(),
        "Temp_C": temp,
        "Humidity": humidity,
        "Wind_Kph": wind_kph,
        "Pressure_mb": pressure,
        "Precip_mm": precip,  # rainfall feature used by the ML pipeline
        "source": source,
    }


def _fetch_openweather(district: str, lat: float, lon: float, cfg: WeatherConfig) -> dict[str, Any]:
    """
    OpenWeatherMap current-weather endpoint.
    Map: main.temp, main.humidity, wind.speed (m/s -> km/h), main.pressure, rain.1h.
    """
    if not cfg.openweather_api_key:
        raise RuntimeError("OPENWEATHER_API_KEY is not set")
    resp = requests.get(
        cfg.openweather_url,
        params={"lat": lat, "lon": lon, "appid": cfg.openweather_api_key, "units": "metric"},
        timeout=cfg.request_timeout,
    )
    resp.raise_for_status()
    payload = resp.json()
    rain = payload.get("rain") or {}
    precip = float(rain.get("1h", rain.get("3h", 0.0)) or 0.0)
    wind_ms = float((payload.get("wind") or {}).get("speed", 0.0) or 0.0)
    main = payload.get("main") or {}
    return _normalize_record(
        district,
        float(main.get("temp", 20.0)),
        float(main.get("humidity", 50.0)),
        wind_ms * 3.6,
        float(main.get("pressure", 1010.0)),
        precip,
        "openweather",
    )


def _fetch_imd(district: str, lat: float, lon: float, cfg: WeatherConfig) -> dict[str, Any]:
    """
    IMD live-weather hook.

    Replace IMD_API_URL with an authorized IMD / AWS endpoint. Expected JSON keys
    can be remapped here without touching ResourceAgent.
    """
    if not cfg.imd_api_url:
        raise RuntimeError("IMD_API_URL is not set")
    headers = {"Authorization": f"Bearer {cfg.imd_api_key}"} if cfg.imd_api_key else {}
    resp = requests.get(
        cfg.imd_api_url,
        params={"lat": lat, "lon": lon, "station": district},
        headers=headers,
        timeout=cfg.request_timeout,
    )
    resp.raise_for_status()
    payload = resp.json()
    return _normalize_record(
        district,
        float(payload.get("temperature", payload.get("Temp_C", 20.0))),
        float(payload.get("humidity", payload.get("Humidity", 50.0))),
        float(payload.get("wind_kph", payload.get("Wind_Kph", 10.0))),
        float(payload.get("pressure", payload.get("Pressure_mb", 1010.0))),
        float(payload.get("rainfall", payload.get("Precip_mm", 0.0))),
        "imd",
    )


def _fetch_openmeteo(district: str, lat: float, lon: float, cfg: WeatherConfig) -> dict[str, Any]:
    resp = requests.get(
        cfg.openmeteo_url,
        params={
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation,surface_pressure",
        },
        timeout=cfg.request_timeout,
    )
    resp.raise_for_status()
    data = resp.json().get("current") or {}
    return _normalize_record(
        district,
        float(data.get("temperature_2m", 20.0)),
        float(data.get("relative_humidity_2m", 50.0)),
        float(data.get("wind_speed_10m", 10.0)),
        float(data.get("surface_pressure", 1010.0)),
        float(data.get("precipitation", 0.0)),
        "openmeteo",
    )


def _provider_chain(cfg: WeatherConfig) -> list[str]:
    mode = (cfg.provider or "auto").lower()
    if mode == "dummy":
        return ["dummy"]
    if mode in {"openweather", "openweathermap"}:
        return ["openweather", "openmeteo", "dummy"]
    if mode == "imd":
        return ["imd", "openmeteo", "dummy"]
    if mode == "openmeteo":
        return ["openmeteo", "dummy"]
    # auto: prefer OpenWeather when a key exists, else Open-Meteo
    if cfg.openweather_api_key:
        return ["openweather", "openmeteo", "dummy"]
    return ["openmeteo", "dummy"]


def _fetch_one(district: str, info: dict[str, Any], fetchers: list[str], cfg: WeatherConfig) -> dict[str, Any]:
    lat, lon = info["coordinates"]
    last_error: Exception | None = None
    for name in fetchers:
        if name == "dummy":
            continue
        try:
            if name == "openweather":
                return _fetch_openweather(district, lat, lon, cfg)
            if name == "imd":
                return _fetch_imd(district, lat, lon, cfg)
            if name == "openmeteo":
                return _fetch_openmeteo(district, lat, lon, cfg)
        except Exception as exc:
            last_error = exc
            continue
    rng = random.Random(sum(ord(ch) for ch in district) % 10_000)
    rec = _normalize_record(
        district,
        round(rng.uniform(5, 32), 2),
        round(rng.uniform(30, 90), 2),
        round(rng.uniform(2, 40), 2),
        round(rng.uniform(990, 1022), 2),
        round(rng.uniform(0, 12), 2),
        f"dummy_fallback:{last_error}" if last_error else "dummy",
    )
    return rec


def fetch_live_weather(cfg: WeatherConfig | None = None) -> tuple[pd.DataFrame, str]:
    """
    Concurrent district fetches. Returns (frame, source_label).

    Never raises for missing APIs: always falls back to dummy weather so the
    ML pipeline stays within the report latency budget.
    """
    cfg = cfg or weather_config()
    chain = _provider_chain(cfg)
    if chain == ["dummy"]:
        return dummy_weather_frame(), "dummy"

    live_fetchers = [name for name in chain if name != "dummy"]
    records: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=cfg.max_workers) as pool:
        futures = {
            pool.submit(_fetch_one, district, info, live_fetchers, cfg): district
            for district, info in district_data.items()
        }
        for fut in as_completed(futures):
            records.append(fut.result())

    if not records:
        return dummy_weather_frame(), "dummy"

    df = pd.DataFrame(records)
    sources = sorted({str(s) for s in df["source"].unique()})
    label = ",".join(sources)
    return df, label
