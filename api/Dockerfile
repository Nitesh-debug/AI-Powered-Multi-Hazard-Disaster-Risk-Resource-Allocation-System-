FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    JK_DISASTER_SQLITE_PATH=/app/data/runtime/jk_disaster_demo.sqlite3

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1
COPY requirements-api.txt ./requirements-api.txt
RUN pip install --no-cache-dir -r requirements-api.txt

COPY api ./api
RUN mkdir -p ./scripts
COPY scripts/__init__.py ./scripts/__init__.py
COPY scripts/build_weather_features.py ./scripts/build_weather_features.py
COPY scripts/prepare_phase7_model_ready_datasets.py ./scripts/prepare_phase7_model_ready_datasets.py
COPY models/development/phase7f_selected ./models/development/phase7f_selected
COPY data/development/replay_features/phase8_historical_replay_2025-10-31.json ./data/development/replay_features/phase8_historical_replay_2025-10-31.json
COPY data/development/phase9_simulated_scenario_v1.json ./data/development/phase9_simulated_scenario_v1.json
COPY data/development/phase9_simulated_weather_fixture_v1.json ./data/development/phase9_simulated_weather_fixture_v1.json

EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
