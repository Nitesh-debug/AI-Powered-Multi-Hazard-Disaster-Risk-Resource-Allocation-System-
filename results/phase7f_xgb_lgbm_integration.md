# Phase 7F v1: XGBoost/LightGBM Integration

**Scope:** SYNTHETIC_DEVELOPMENT_ONLY (`phase7a_v1`). This experiment does not train on verified disaster outcomes and does not establish real-world forecasting skill.

## Data and Labels

Each of the six Phase 7C hazard datasets contains 42,480 chronological district-days and 68 one-day-lagged weather predictors: 14,480 train rows (2020-01-08 through 2021-12-31), 7,300 validation rows (2022-01-01 through 2022-12-31), and 20,700 test rows (2023-01-01 through 2025-10-31). The validation and test periods follow the training period. The same 20 districts appear across periods; transfer to unseen districts was not tested.

| Hazard | Train positives | Validation positives | Test positives | Test negatives |
| --- | ---: | ---: | ---: | ---: |
| Flood | 47 | 27 | 92 | 20,608 |
| Heavy rain | 346 | 161 | 624 | 20,076 |
| Landslide | 64 | 32 | 81 | 20,619 |
| Heatwave | 349 | 712 | 2,958 | 17,742 |
| Coldwave | 316 | 155 | 1,491 | 19,209 |
| Windstorm | 121 | 156 | 367 | 20,333 |

These are generated synthetic-rule targets, not event observations. Separately, verified project-period flood evidence remains 32 positive district-days, zero confirmed negative district-days, and 42,588 unknown days out of 42,620; the 32 positives cover 15 of 20 districts. Accepted verified labels for the other five hazards remain zero. Unknown days were not relabelled negative, and no verified label files were changed.

The processed source hashes before and after implementation match:

- `data/processed/weather_features.csv`: `18eeac8a77735db0e408e0e5c685f3ac4c65eac3fd6d22f0bec6c805c4a65df0`
- `data/processed/daily_flood_dataset.csv`: `609154b4f62a4628f464decbb668722d230386580b69f872db53cc6704d172a2`

## Experiment

The Phase 7F comparison is versioned independently of Phase 7D and 7E. It refit eight candidates for each hazard: the five fixed Phase 7D algorithms, the Phase 7E selected incumbent with its frozen parameters, and tuned XGBoost and LightGBM. Prior 7D/7E and Phase 7D XGBoost/LightGBM validation metrics are retained as reference values; candidate selection uses fresh Phase 7F fits.

XGBoost and LightGBM each received 20 deterministic randomized configurations per hazard (240 configurations total), using three expanding, non-overlapping target-date folds inside training (720 successful fold fits). All districts for a target date stayed together. `scale_pos_weight` was derived from each fitting fold only. All 240 configurations completed successfully. Summed CV fit time was 818.47 seconds; the 48 candidate train fits took 57.42 seconds. Random seed: 42. Runtime: Python 3.11.14, scikit-learn 1.8.0, XGBoost 3.2.0, LightGBM 4.7.0, pandas 2.3.3, NumPy 2.4.1, SciPy 1.17.0, joblib 1.5.3.

Candidate selection ranked validation Average Precision (AP), then validation ROC-AUC, then false-alarm rate at 0.50, then candidate ID for exact ties. Thresholds were selected from 0.10 through 0.90 by validation F1; ties prefer precision, recall, lower false-alarm rate, then lower threshold. No calibration was fitted. Brier values are raw-score diagnostics and must not be interpreted as calibrated probability quality.

## Selected Validation Results

Each selected entry is the candidate with the highest validation AP under the procedure above, not a claim of real-world skill.

| Hazard | Selected candidate | Validation AP | ROC-AUC | Threshold | Precision | Recall | F1 | False-alarm rate | Brier diagnostic |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Flood | Tuned XGBoost | 0.1071 | 0.7849 | 0.30 | 0.1818 | 0.2222 | 0.2000 | 0.0037 | 0.0048 |
| Heavy rain | Phase 7D Logistic Regression | 0.1761 | 0.8338 | 0.80 | 0.1792 | 0.3540 | 0.2380 | 0.0366 | 0.1154 |
| Landslide | Phase 7E Extra Trees incumbent refit | 0.0387 | 0.8959 | 0.10 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0043 |
| Heatwave | Phase 7D Extra Trees | 0.4539 | 0.8836 | 0.50 | 0.3915 | 0.5829 | 0.4684 | 0.0979 | 0.0940 |
| Coldwave | Phase 7D HistGradientBoosting | 0.0908 | 0.8141 | 0.10 | 0.1055 | 0.1871 | 0.1349 | 0.0344 | 0.0207 |
| Windstorm | Phase 7E Random Forest incumbent refit | 0.0878 | 0.8022 | 0.20 | 0.0746 | 0.3654 | 0.1239 | 0.0990 | 0.0293 |

The landslide validation operating point predicted no positives (F1 and recall both 0); its test recall was also zero. This is a material development limitation, not a reason to adjust the threshold using test data.

## One-Time Test Evaluation

The models and thresholds were frozen before the Phase 7F evaluator read test rows. It evaluated 20,700 rows for each of six targets (124,200 hazard-row evaluations) and recorded six overall, 120 district, and 24 seasonal metric rows. Subgroup metrics are withheld when either class has fewer than five examples; support counts remain recorded.

| Hazard | Positive / negative | Frozen threshold | AP | ROC-AUC | Precision | Recall | F1 | False-alarm rate | Raw-score Brier diagnostic |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Flood | 92 / 20,608 | 0.30 | 0.0592 | 0.8455 | 0.1157 | 0.1522 | 0.1315 | 0.0052 | 0.0059 |
| Heavy rain | 624 / 20,076 | 0.80 | 0.2063 | 0.8417 | 0.2185 | 0.4199 | 0.2874 | 0.0467 | 0.1266 |
| Landslide | 81 / 20,619 | 0.10 | 0.0198 | 0.8586 | 0.0000 | 0.0000 | 0.0000 | 0.0002 | 0.0039 |
| Heatwave | 2,958 / 17,742 | 0.50 | 0.3811 | 0.7732 | 0.4148 | 0.3908 | 0.4024 | 0.0919 | 0.1219 |
| Coldwave | 1,491 / 19,209 | 0.10 | 0.1843 | 0.7603 | 0.2486 | 0.0892 | 0.1313 | 0.0209 | 0.0682 |
| Windstorm | 367 / 20,333 | 0.20 | 0.0439 | 0.6918 | 0.0409 | 0.2807 | 0.0714 | 0.1188 | 0.0307 |

The same 2023-01-01 through 2025-10-31 interval had already been evaluated for Phase 7E. Phase 7F did not use prior or current test metrics for selection, but this interval is not an untouched project-wide holdout. The attempt marker at `results/ml/phase7f/final_test_evaluation_attempt.json` records `completed_once`; do not run the Phase 7F evaluator again.

## Integration

- Six versioned model/metadata pairs are stored under `models/development/phase7f_selected/`. Registry version: `phase7f_v1`; feature contract: `phase5_68_shifted_weather_v1`; dataset: `phase7c_v1`; synthetic rules: `phase7a_v1`. Every model file has a SHA-256 hash and test-evaluation seal.
- FastAPI loads only Phase 7F artifacts. Responses expose `raw_model_score`, the validation raw-score threshold, district, feature-reference date, target date, model version, synthetic scope, active signals, and the unweighted combined development score (maximum raw hazard score). `calibrated_probability` is explicitly false.
- Open-Meteo remains the live provider behind a `WeatherFeatureProvider` protocol. Only the existing Srinagar smoke test is claimed; full 20-district live coverage is unverified. Tomorrow.io and other providers have no credentials or implementation.
- Allocation remains `SIMULATION_ONLY_NOT_FOR_DISPATCH` with fixed demo inventory (4 team slots, 50 medical-kit slots, 60 water-crate slots). Population/exposure, vulnerability, real resource availability, suitability, travel time, and capacity are explicitly returned as unavailable.
- The React/Leaflet dashboard displays raw scores and validation thresholds, combined max-score semantics, synthetic scope, and unavailable operational inputs. Map locations remain weather reference points, not inferred boundaries.
- SQLite remains active. The Supabase server-side mirror and RLS schema are scaffolding only; no project credentials or connected service were available. Alerts are development records; outbound notifications remain disabled.

## Validation and Reproduction

Passed: 240/240 tuning configurations; Phase 7F selection validation reproducing all six validation metric/threshold sets and hashes; final report validation; Phase 7D baseline validation (30 artifacts); Phase 7E selection validation (six models); Phase 7E sealed-report validation; Phase 8 replay validation (20 districts × 68 features); ten API/Phase 7F unit tests; frontend TypeScript check and Vite production build. The processed weather and flood files retain their pre-run SHA-256 hashes.

Reproduce selection in a clean checkout using Python 3.11 and `requirements-api.txt`:

```powershell
python scripts/tune_phase7f_models.py
python scripts/validate_phase7f_selection.py
```

Only after selection freezes, evaluate the test split once:

```powershell
python scripts/evaluate_phase7f_final_test.py
python scripts/validate_phase7f_final_test_report.py
```

Run the focused tests and frontend build:

```powershell
python -m unittest tests.test_phase8_api tests.test_phase7f_experiment -v
cd frontend
npm ci
npm run build
```

The final evaluator refuses repeat access. Docker was not available in this environment, GitHub Actions were not executed, and no production deployment was attempted. The legacy `tests.test_agents` suite had five passes and one pre-existing `test_canonical_outputs` failure when run with isolated temporary storage; it is outside the Phase 7F API path.
