"""Runtime configuration for weather, storage, and latency targets."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SCRIPTS_DIR = PROJECT_ROOT / "scripts"
RESULTS_DIR = PROJECT_ROOT / "results"
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "disaster_system.db"

# Chapter 5 report benchmarks
PREDICTION_SLA_SECONDS = 0.3
ALLOCATION_SLA_SECONDS = 1.0


@dataclass(frozen=True)
class WeatherConfig:
    """
    Live weather providers (swap order without changing ML code):

    1. OpenWeatherMap — set OPENWEATHER_API_KEY
       GET https://api.openweathermap.org/data/2.5/weather
    2. IMD / India Meteorological Department — optional IMD_API_URL + IMD_API_KEY
       (authorized endpoint; left as a documented hook)
    3. Open-Meteo — no key, default public fallback
    4. Dummy / historical CSV — offline last resort
    """

    provider: str = os.getenv("WEATHER_PROVIDER", "auto")
    openweather_api_key: str | None = os.getenv("OPENWEATHER_API_KEY") or os.getenv("OPENWEATHERMAP_API_KEY")
    openweather_url: str = os.getenv(
        "OPENWEATHER_URL",
        "https://api.openweathermap.org/data/2.5/weather",
    )
    imd_api_url: str | None = os.getenv("IMD_API_URL")
    imd_api_key: str | None = os.getenv("IMD_API_KEY")
    openmeteo_url: str = os.getenv("OPENMETEO_URL", "https://api.open-meteo.com/v1/forecast")
    request_timeout: float = float(os.getenv("WEATHER_TIMEOUT", "4"))
    max_workers: int = int(os.getenv("WEATHER_MAX_WORKERS", "8"))


@dataclass(frozen=True)
class StorageConfig:
    sqlite_path: Path = DB_PATH
    supabase_url: str | None = os.getenv("SUPABASE_URL")
    supabase_key: str | None = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY")


def weather_config() -> WeatherConfig:
    return WeatherConfig()


def storage_config() -> StorageConfig:
    return StorageConfig()
