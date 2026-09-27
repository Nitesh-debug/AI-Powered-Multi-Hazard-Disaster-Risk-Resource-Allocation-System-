# JK Multi-Hazard Disaster Risk and Resource Allocation System

A research and development prototype for Jammu & Kashmir that combines historical weather features, synthetic-only hazard experiments, a FastAPI service, a React/Leaflet console, and simulated resource planning.

> **Development prototype only.** Model targets and resource/exposure inputs are synthetic. Scores are uncalibrated and must not be used for public warnings, emergency decisions, or real dispatch.

## Contents

- [Project Status](#project-status)
- [Scientific Scope and Data](#scientific-scope-and-data)
- [Capabilities](#capabilities)
- [Repository Structure](#repository-structure)
- [Quick Start](#quick-start)
- [Demo Modes](#demo-modes)
- [API](#api)
- [Validation](#validation)
- [Persistence and Configuration](#persistence-and-configuration)
- [Docker and CI](#docker-and-ci)
- [Documentation and Reports](#documentation-and-reports)
- [Safety and Limitations](#safety-and-limitations)

## Project Status

| Phase | Scope | Status |
| --- | --- | --- |
| 1-3 | Historical weather collection, merging, feature engineering | Complete at research level |
| 4-6 | Disaster evidence assessment, dataset design, label/source audit | Documented; verified negative-label evidence remains unavailable |
| 7 | Synthetic labels, chronological model-ready data, baselines, selection and evaluation | Complete for development experiments only |
| 8 | Historical replay and live-weather adapter | Local prototype; all-district live coverage unverified |
| 9 | FastAPI service and simulated scenario | Implemented and locally tested |
| 10 | Supabase | SQL and optional mirror scaffold; not connected |
| 11 | React + Leaflet | Local development UI implemented |
| 12 | Alerts and resource planning | Development simulation only |
| 13 | Testing | Local test suite passes; hosted CI has not been observed |
| 14 | Deployment | Configuration exists; production deployment is not complete |

For detailed implementation status and test evidence, see [the final completion report](results/final_completion_report.md), [the phase status](results/final_project_status.md), and [the completion gap analysis](results/final_completion_gap_analysis.md).

## Scientific Scope and Data

- The weather panel covers **20 selected district points**, 2020-01-01 through 2025-10-31: **1,022,880 hourly rows** and **42,620 district-days**.
- One-day-ahead model inputs use **68 prior-day weather features**. Target-date weather is not a predictor.
- The current flood panel contains **32 verified positive district-days**, **0 verified negative district-days**, and **42,588 unknown district-days**. `NO_VERIFIED_EVENT` is unknown, never a negative label.
- The other five hazard tracks (heavy rain, landslide, heatwave, coldwave, windstorm) have **0 accepted verified project-period event labels** in the current assessment.
- Phase 7 labels are marked `SYNTHETIC_DEVELOPMENT_ONLY`; rule version `phase7a_v1`. They represent transparent weather-rule outcomes, not historical disasters.
- Phase 9 resources, exposure, vulnerability, travel estimates, and demo weather are separately marked synthetic/simulated. They are not official inventories, population estimates, road routes, observations, or forecasts.
- Historical raw and processed CSV panels are intentionally excluded from this Git repository. They are large research inputs and are not needed for the deterministic replay/demo path. `data/raw/` and `data/processed/` are ignored by Git; the generation/validation scripts remain in `scripts/`.

The six development model scores are uncalibrated and measure reproduction of synthetic rules only. See [data and labels](docs/data_and_labels.md), [ML pipeline](docs/ml_pipeline.md), and [limitations](docs/limitations.md) before interpreting any output.

## Capabilities

- Historical replay from a fixed, label-free 20-district snapshot.
- Optional Open-Meteo ECMWF live-weather adapter. A district is unavailable if the prior-day feature contract is incomplete; missing values are not silently imputed.
- Six Phase 7F synthetic-development model outputs with validation thresholds and explicit development-warning metadata.
- A deterministic offline demo-weather fixture for all 20 districts.
- Resource and exposure APIs plus an explainable simulated planning workflow with hazard suitability, capacity, travel-limit, and unique-resource constraints.
- SQLite persistence for development runs, signals, and simulated plans.
- React/Leaflet UI with weather reference points and a dedicated resource-planning view.

The map markers are weather lookup points, not district boundaries or verified district centroids.

## Repository Structure

```text
.
|-- README.md                         Project overview, setup, and safety limits
|-- IMPLEMENTATION_COMPLETION_REPORT.md
|-- EXECUTION_SUMMARY.md
|-- agent_app.py                      Legacy Streamlit prototype
|-- agents/                           Legacy prototype agents
|-- api/                              FastAPI routes, models, weather, storage, planning
|-- automation/                       Earlier weather notebook workflow
|-- data/
|   |-- development/                  Synthetic datasets, replay and simulated fixtures
|   |-- raw/                           Local-only source data; excluded from Git
|   |-- processed/                     Local-only derived weather panels; excluded from Git
|   `-- runtime/                       Local SQLite database; excluded from Git
|-- db/migrations/                    Development-only Supabase schema
|-- docs/                             Architecture, data, ML, risk, API, deployment notes
|-- frontend/                         React, TypeScript, Vite, Leaflet console
|-- models/development/               Synthetic-development model artifacts
|-- results/                          Research reports, validation summaries, metrics
|-- scripts/                          Collection, engineering, training, evaluation, validators
|-- storage/                          Legacy prototype persistence
|-- tests/                            Unit and API tests
|-- ui/                               Legacy prototype UI helpers
|-- .github/workflows/                CI workflow definition
|-- docker-compose.yml                Local container orchestration
|-- requirements-api.txt              Pinned API/model Python dependencies
`-- requirements.txt                 Legacy prototype dependencies
```

Local smoke-test prediction/allocation snapshots under `results/` are ignored. Static research reports and validation artifacts are versioned.

## Quick Start

Prerequisites: Python 3.11, Node.js 22, and npm. The checked-in replay snapshot, selected development models, and simulated fixtures support local use without the raw/processed weather CSVs.

Create the Python environment from the repository root:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-api.txt
```

Start the API in one terminal:

```powershell
python -m uvicorn api.main:app --reload --port 8000
```

Start the web app in a second terminal:

```powershell
Set-Location frontend
npm ci
$env:VITE_API_PROXY_TARGET = 'http://127.0.0.1:8000'
npm run dev -- --host 127.0.0.1 --port 5173
```

Open [http://127.0.0.1:5173](http://127.0.0.1:5173). The API health endpoint is [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health), and interactive API documentation is at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

If those ports are occupied, choose unused ports and set `VITE_API_PROXY_TARGET` to the API address.

## Demo Modes

- **Historical replay:** label-free features from `data/development/replay_features/phase8_historical_replay_2025-10-31.json`, reference date 2025-10-30, target date 2025-10-31.
- **Live weather:** requests recent and forecast weather through Open-Meteo ECMWF and constructs only the complete prior local day. This requires network access; coverage and service availability are not guaranteed for all 20 districts.
- **Simulated demo:** fixed `SIMULATED_DEMO_WEATHER` fixture for 20 districts × 68 features. This is deterministic development data, not current weather.

Select a mode in the UI and run an assessment. Use Resource Planning to inspect the separate simulated scenario. Every planning result is marked `SIMULATION_ONLY_NOT_FOR_DISPATCH`.

## API

Core routes include:

| Method | Route | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | API readiness and runtime diagnostics |
| `GET` | `/api/districts` | District reference points |
| `GET` | `/api/registry` | Development model registry |
| `POST` | `/api/predictions` | Replay, live, or simulated-demo assessment |
| `GET` | `/api/alerts` | Persisted development signals |
| `GET` | `/api/runs` | Stored assessment runs |
| `GET` | `/api/resources` | Simulated resource catalog |
| `GET` | `/api/resources/{resource_id}` | One simulated resource |
| `GET` | `/api/exposure` | Simulated exposure/vulnerability rows |
| `GET` | `/api/response-plan?run_id=...` | Recommendations for an assessment run |
| `POST` | `/api/allocations/simulate` | Build and persist a simulated allocation plan |

`POST /api/allocations` remains a compatibility alias. Resource planning uses **140 simulated resource records** (7 types × 20 district points), **20 simulated exposure rows**, and **400 ordered travel estimates**. Travel uses a straight-line heuristic, not road routing. Operational inputs are reported unavailable.

## Validation

Run the complete local test suite:

```powershell
python -m unittest discover -s tests -v
```

Run targeted simulation/configuration checks:

```powershell
python -m unittest tests.test_phase9_simulation -v
python scripts/validate_phase9_simulation.py
python scripts/validate_runtime_config.py
python scripts/validate_phase8_replay_snapshot.py
python scripts/validate_phase7f_selection.py
python scripts/validate_phase7f_final_test_report.py
```

Build the frontend:

```powershell
Set-Location frontend
npm ci
npm run build
```

The Phase 7F one-time final-test evaluator is sealed after its recorded run. **Do not rerun `scripts/evaluate_phase7f_final_test.py`**; use the saved final report validator instead. Training/research scripts may require the locally held raw and processed datasets, which are deliberately not pushed to GitHub.

## Persistence and Configuration

SQLite is the default local persistence layer. It stores development prediction runs, signals, and simulated allocations under `data/runtime/`.

Optional Supabase settings are documented in `.env.example`. Apply `db/migrations/001_phase9_development_schema.sql` only to an authorized development project. Keep `.env` and service-role credentials out of source control and browser bundles. No Supabase project is currently connected; SQLite remains active.

## Docker and CI

With Docker Engine and Compose installed:

```powershell
docker compose up --build
```

The web UI binds to `127.0.0.1:8080` by default; API listens on the internal container network. GitHub Actions defines Python tests, artifact/config validation, frontend build, and container builds. Docker execution, hosted CI, and production deployment have not been verified in this environment.

## Documentation and Reports

- [Architecture](docs/architecture.md)
- [Data and labels](docs/data_and_labels.md)
- [ML pipeline](docs/ml_pipeline.md)
- [Risk engine](docs/risk_engine.md)
- [Resource allocation](docs/resource_allocation.md)
- [API](docs/api.md)
- [Deployment](docs/deployment.md)
- [Limitations](docs/limitations.md)
- [Final completion report](results/final_completion_report.md)
- [Current phase status](results/final_project_status.md)
- [Completion gap analysis](results/final_completion_gap_analysis.md)

## Safety and Limitations

- Historical source absence is not evidence of a non-event. Unknown labels remain unknown.
- Synthetic model metrics do not establish real-world disaster forecasting skill.
- Risk outputs are uncalibrated development scores, not probabilities or government warning categories.
- Simulated population, vulnerability, resources, and travel do not describe real operational assets.
- The service has no user authentication or production threat review. Do not expose publicly or dispatch from its outputs.
- Verified labels, all-district live-weather validation, connected cloud persistence, production security, and deployment remain outstanding.

Author: Nitesh Kumar
