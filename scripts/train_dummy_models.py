"""Train a Random Forest risk model on Temperature, Rainfall, and Humidity features."""

from __future__ import annotations

import random
import sys
import time
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler

SCRIPTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPTS_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.district_info import district_data  # noqa: E402
from scripts.settings import DATA_DIR  # noqa: E402


def generate_training_frame(n_records: int = 800, seed: int = 42) -> pd.DataFrame:
    rng = random.Random(seed)
    districts = list(district_data.keys())
    rows: list[dict[str, float | str | int]] = []
    for _ in range(n_records):
        district = rng.choice(districts)
        temp = rng.uniform(-5, 35)
        humidity = rng.uniform(20, 95)
        wind = rng.uniform(0, 55)
        pressure = rng.uniform(975, 1025)
        rainfall = rng.uniform(0, 25)  # Precip_mm / rainfall
        risk = 0
        if rainfall > 10 or wind > 30 or humidity > 85:
            risk = 1
        if rainfall > 15 and wind > 40:
            risk = 2
        if rainfall > 18 and wind > 45:
            risk = 3
        rows.append(
            {
                "District": district,
                "Fetch_Time_UTC": "2023-10-01 10:00:00",
                "Temp_C": temp,
                "Humidity": humidity,
                "Wind_Kph": wind,
                "Pressure_mb": pressure,
                "Precip_mm": rainfall,
                "Rainfall_mm": rainfall,
                "Risk_Level": risk,
            }
        )
    return pd.DataFrame(rows)


def train_and_save(df: pd.DataFrame) -> dict[str, float]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = SCRIPTS_DIR / "jk_weather_history_enhanced.csv"
    df.to_csv(csv_path, index=False)
    df.to_csv(DATA_DIR / "jk_weather_history_enhanced.csv", index=False)

    feature_cols = ["Temp_C", "Humidity", "Wind_Kph", "Pressure_mb", "Precip_mm"]
    x = df[feature_cols]
    y = df["Risk_Level"]
    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.2, random_state=42)

    scaler = StandardScaler()
    x_train_s = scaler.fit_transform(x_train.to_numpy())
    x_test_s = scaler.transform(x_test.to_numpy())

    model = RandomForestClassifier(n_estimators=80, random_state=42, n_jobs=-1)
    model.fit(x_train_s, y_train)

    started = time.perf_counter()
    _ = model.predict(x_test_s)
    inference_seconds = time.perf_counter() - started

    print(classification_report(y_test, model.predict(x_test_s), zero_division=0))
    print(f"Batch inference on holdout set: {inference_seconds:.4f}s")

    encoder = LabelEncoder()
    encoder.fit(list(district_data.keys()))

    joblib.dump(model, SCRIPTS_DIR / "disaster_prediction_model.pkl")
    joblib.dump(scaler, SCRIPTS_DIR / "scaler.pkl")
    joblib.dump(encoder, SCRIPTS_DIR / "district_encoder.pkl")
    joblib.dump(feature_cols, SCRIPTS_DIR / "feature_columns.pkl")
    return {"holdout_inference_seconds": inference_seconds}


def main() -> None:
    print("Generating dummy weather data...")
    frame = generate_training_frame()
    metrics = train_and_save(frame)
    print("Model training complete. Metrics:", metrics)


if __name__ == "__main__":
    main()
