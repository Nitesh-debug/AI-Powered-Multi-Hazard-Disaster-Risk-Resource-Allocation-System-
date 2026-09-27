# JK Disaster Management System: Final Project Status

**Status date:** 2026-09-27
**Project status:** research/development prototype; not an operational warning or dispatch system.

## Phases

- Existing project phases 1-5 remain complete at the documented data-pipeline/research level: historical weather collection, merging, feature engineering, disaster-data assessment, and ML dataset design.
- Phase 6 label strategy and source coverage are documented. Verified event sources do not currently support sufficiently complete auditable district-date no-flood labels.
- Phase 7A-7C synthetic rule design, generation, and model-ready chronological datasets remain versioned separately from verified labels.
- Phase 7D baselines and Phase 7E tuning/final evaluation remain preserved and validate successfully.
- Newly completed Phase 7F adds separate XGBoost/LightGBM tuning, validation-only comparison, frozen thresholds, one-time final evaluation, model registry version, API/risk integration, tests, and documentation.
- Phase 8 replay/live-weather work remains a prototype; a deterministic, clearly labelled simulated-weather path is available for offline demonstration. Live weather coverage is not confirmed for all districts.
- Phase 9 FastAPI and Phase 11 React/Leaflet are implemented for local development. Resource/exposure/response-plan endpoints and a constrained, explainable simulated allocation workflow are available.
- Phase 10 Supabase remains an optional schema/REST-mirror scaffold; no project or credentials are configured, and SQLite remains the active local store.
- Phase 12 alerts and resource allocation are development simulations only. Phase 13's local automated suite passes; hosted CI has not been observed. Phase 14 has container/Compose/CI configuration but no verified image build or deployment. No production security review or operational readiness is claimed.

## Data and Scientific Limits

Every Phase 7F model uses `SYNTHETIC_DEVELOPMENT_ONLY` labels version `phase7a_v1`; none uses verified historical disaster outcomes. Phase 7C contributes 42,480 rows per hazard, 68 prior-day features, with 14,480 train rows, 7,300 validation rows, and 20,700 test rows. The split is chronological; the same 20 districts recur over periods, so spatial transfer was not evaluated.

Verified flood evidence available for the project period is 32 positive district-days across 15 of 20 districts, zero confirmed verified negatives, and 42,588 unknown days out of 42,620. Accepted verified labels for heavy rain, landslide, heatwave, coldwave, and windstorm are all zero. `NO_VERIFIED_EVENT` remains unknown, not a negative. No synthetic label was presented as a historical event.

The Phase 7E and Phase 7F evaluations use the same 2023-01-01 through 2025-10-31 test interval. Phase 7F selection did not use test metrics and its evaluator was run once after selection froze, but the shared interval is not an independent project-wide pristine holdout. Phase 7F raw scores are not calibrated probabilities. The landslide selected validation threshold yielded zero validation positives and zero test recall.

## Selected Phase 7F Models

Candidates were compared by validation AP among five Phase 7D baselines, a Phase 7E incumbent refit, and tuned XGBoost/LightGBM. XGBoost and LightGBM each had 20 configurations per hazard and three expanding date-block folds within train: 240 configurations, 720 successful fold fits, 818.47 summed CV fit seconds. All 48 final candidates were freshly fit on train. Thresholds were selected on validation by maximum F1 over 0.10-0.90.

| Hazard | Selected candidate | Validation AP | Validation threshold | Test AP | Test ROC-AUC | Test precision | Test recall | Test F1 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Flood | Tuned XGBoost | 0.1071 | 0.30 | 0.0592 | 0.8455 | 0.1157 | 0.1522 | 0.1315 |
| Heavy rain | Logistic Regression baseline | 0.1761 | 0.80 | 0.2063 | 0.8417 | 0.2185 | 0.4199 | 0.2874 |
| Landslide | Phase 7E Extra Trees incumbent refit | 0.0387 | 0.10 | 0.0198 | 0.8586 | 0.0000 | 0.0000 | 0.0000 |
| Heatwave | Extra Trees baseline | 0.4539 | 0.50 | 0.3811 | 0.7732 | 0.4148 | 0.3908 | 0.4024 |
| Coldwave | HistGradientBoosting baseline | 0.0908 | 0.10 | 0.1843 | 0.7603 | 0.2486 | 0.0892 | 0.1313 |
| Windstorm | Phase 7E Random Forest incumbent refit | 0.0878 | 0.20 | 0.0439 | 0.6918 | 0.0409 | 0.2807 | 0.0714 |

Test false-alarm rates were 0.0052 flood, 0.0467 heavy rain, 0.0002 landslide, 0.0919 heatwave, 0.0209 coldwave, and 0.1188 windstorm. These values measure reproduction of synthetic rules only; they do not establish disaster forecasting performance.

Detailed validation/test metrics, candidate comparisons, confusion counts, runtime, subgroup rules, and score semantics are in `results/phase7f_xgb_lgbm_integration.md`. Trial, metric, threshold, selection, and final evaluation artifacts are in `results/ml/phase7f/`.

## Runtime and Integrations

- Model registry: six models at `models/development/phase7f_selected/`, version `phase7f_v1`, each with a SHA-256 and completed-once test metadata.
- API: preserves `/api/health`, `/api/districts`, `/api/registry`, `/api/predictions`, `/api/allocations`, `/api/alerts`, and `/api/runs`. Per-hazard raw score, validation threshold, date alignment, district, model version, label scope, active signals, and max-raw-score combined development risk are exposed.
- Live weather: Open-Meteo ECMWF behind a provider protocol; Srinagar smoke test only. All-district live coverage is unverified; no Tomorrow.io credentials/provider are present.
- Frontend: React/TypeScript/Vite/Leaflet build passed to temporary output. It shows raw, uncalibrated score semantics and weather reference points; it does not infer district boundaries.
- Resource allocation: a separate Phase 9 scenario artifact contains 140 simulated resource records (7 types across 20 district points), 20 simulated exposure/vulnerability records, and 400 ordered district travel estimates. These are illustrative inputs, not official inventory or population data. The deterministic engine applies hazard suitability, stock/capacity, one-use resource IDs within a plan, a simulated 240-minute travel limit, and records allocation reasons. Estimated travel is straight-line distance adjusted by a fixed factor and speed/delay assumptions, not road routing. Outputs remain `SIMULATION_ONLY_NOT_FOR_DISPATCH`.
- Alerts: six-hazard development alert levels, component reasons, model/source/timestamp metadata, and explicit synthetic-score semantics are exposed. Thresholds are not official warning levels; outbound notification remains disabled.
- Demo weather: a separate 20-district by 68-feature fixture supports deterministic end-to-end demonstration. Values are explicitly `SIMULATED_DEMO_WEATHER`, not observations or a current forecast.
- Persistence: SQLite development store active. Supabase SQL/RLS scaffold exists, but no account/credentials or connected-service test. Outbound notifications are disabled.
- Security/deployment: no user authentication or operational security review; Docker was unavailable on this host; GitHub-hosted Actions and production deployment were not executed. Do not expose publicly or dispatch from outputs.

## Validation Results

- Phase 7F: all 240 CV configurations passed; 48-candidate selection validator passed; six validation operating points reproduced; one-time final test report validator passed; 6 overall plus 144 subgroup metrics recorded.
- Full local test discovery: 25 tests passed. A final focused Phase 9 rerun passed all 9 Phase 9 tests, including resource constraints, alert metadata, weather-failure containment, and request-size rejection.
- Prior artifact checks: Phase 7D 30/30 model artifacts passed; Phase 7E six selected models and sealed report passed; Phase 8 replay passed for 20 districts × 68 features.
- Phase 9 simulation validation passed: 140 resource records, 20 exposure records, 400 travel pairs, and 20 × 68 labelled demo-weather values.
- Runtime config validation passed: 2 explicit CORS origins, 65,536-byte request-body cap, Supabase not configured; no credential values were printed.
- Python `compileall`, frontend TypeScript check, Vite build, Compose/CI YAML parsing, and `git diff --check` passed. The diff check emitted only Git's LF-to-CRLF notices for three text files.
- Local API and browser smoke checks passed on fallback ports 8002 and 5175. The deterministic demo returned 20/20 district assessments and a simulated allocation example with 15 unique resource IDs and no duplicate use.
- Docker image/Compose execution and remote CI: not run; Docker was unavailable and no hosted CI run was triggered.
- `weather_features.csv` and `daily_flood_dataset.csv` source hashes match before and after; no raw or processed dataset was modified.

## Required Human Actions Before Operational Work

1. Obtain auditable, official district-date reporting that explicitly records nil/no-flood periods and documents coverage/completeness. Keep unreported days unknown.
2. Obtain verified event labels and documented definitions for heavy rain, landslide, heatwave, coldwave, and windstorm.
3. Supply authoritative population/exposure, vulnerability, resource stock/suitability, transport/travel-time, and capacity inputs before designing real allocations.
4. Verify live weather coverage and feature quality across all 20 districts; provide authorized provider credentials if another source is required.
5. Connect and test a user-owned Supabase project only after credentials/policies are supplied; establish authentication, authorization, audit, and notification controls.
6. Provide Docker/CI/deployment environment and an operational security review before any production deployment.
7. Treat the Phase 7F model outputs strictly as synthetic-rule experiments; obtain independently verified event and explicit nil/non-event evidence before any real-label supervised training or skill claim.

## Reproduction Commands

Use Python 3.11 with the pinned versions in `requirements-api.txt`. Run selection in a clean checkout with an empty Phase 7F output/model destination:

```powershell
python scripts/tune_phase7f_models.py
python scripts/validate_phase7f_selection.py
```

Only after model/threshold selection freezes, run the one-shot final evaluation once:

```powershell
python scripts/evaluate_phase7f_final_test.py
python scripts/validate_phase7f_final_test_report.py
```

Do not rerun the evaluator in this workspace; its attempt marker is sealed. Focused checks:

```powershell
python -m unittest tests.test_phase8_api tests.test_phase7f_experiment -v
python scripts/validate_phase7f_selection.py
python scripts/validate_phase7f_final_test_report.py
python -m unittest discover -s tests -v
python scripts/validate_phase9_simulation.py
python scripts/validate_runtime_config.py
```

The local demo can be opened at `http://127.0.0.1:5175/` while this workspace's API is available at `http://127.0.0.1:8002/`. Select the explicitly simulated demo mode; results are not for public warning or dispatch. These local servers are convenience processes, not a deployment.
