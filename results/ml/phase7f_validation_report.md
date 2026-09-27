# Phase 7F Validation Report

**Scope:** versioned synthetic development models only (`phase7f_v1`, `SYNTHETIC_DEVELOPMENT_ONLY`, rule `phase7a_v1`). No raw or processed datasets were modified.

## Experiment Checks

| Check | Result | Evidence |
| --- | --- | --- |
| Boosted search completion | PASS | 240/240 deterministic configurations; three expanding training-date folds each; 720 successful fold fits |
| Candidate matrix | PASS | 48 rows: eight candidates for each of six hazards |
| Dataset boundaries | PASS | Each loader returned only 14,480 train and 7,300 validation rows; test split was absent |
| Temporal folds | PASS | Ordered, non-overlapping date blocks; all district rows for a target date stayed together |
| Imbalance method | PASS | XGBoost/LightGBM `scale_pos_weight` computed from each fit fold only |
| Model selection | PASS | Six selected models; validation AP and threshold results reproduced; model and dataset hashes matched |
| Test evaluation | PASS | One-time sealed run; 20,700 rows per hazard; thresholds unchanged; six overall plus 144 subgroup metric rows |
| Test report validation | PASS | Metadata seals, validation thresholds, class supports and reported metrics consistent; validator did not open datasets or model files |
| Prior artifacts | PASS | Phase 7D (30 models), Phase 7E (six selections and sealed report), and Phase 8 replay (20 × 68) validated |
| API and experiment unit tests | PASS | 10 tests passed: five API tests and five Phase 7F tests |
| Frontend | PASS | TypeScript check and Vite production build completed to a temporary output directory |
| Source integrity | PASS | `weather_features.csv` SHA-256 `18eeac8a77735db0e408e0e5c685f3ac4c65eac3fd6d22f0bec6c805c4a65df0`; `daily_flood_dataset.csv` SHA-256 `609154b4f62a4628f464decbb668722d230386580b69f872db53cc6704d172a2`, unchanged before/after |

## Test Exceptions and Environment Notes

- Legacy `tests.test_agents`: 5 passed, 1 failed. `test_canonical_outputs` did not produce its expected canonical CSV when isolated temporary storage was used. Legacy prototype files were not changed for this Phase 7F task.
- Standard `npm run build` reached Vite but could not unlink a locked existing `frontend/dist/assets/index-CG3CaO-m.css`. TypeScript passed; a direct Vite build to a temporary directory passed. Existing `dist` files were left untouched.
- Docker CLI/Engine was unavailable, so image builds and Compose startup were not run. GitHub Actions were not run.
- Existing Phase 7D/7E sklearn artifacts emitted version warnings when inspected under scikit-learn 1.8.0; historical validators still passed. Phase 7F artifacts and runtime are pinned to the same Python 3.11/scikit-learn 1.8.0/XGBoost 3.2.0/LightGBM 4.7.0 environment.
- Joblib could not discover physical CPU count on this Windows host and fell back to logical cores. The warning did not fail training or tests.

All model metrics remain synthetic-rule development diagnostics. The Phase 7F test interval was previously evaluated by Phase 7E and is therefore not a project-wide pristine holdout. See `results/phase7f_xgb_lgbm_integration.md` for exact model metrics and scientific limitations.
