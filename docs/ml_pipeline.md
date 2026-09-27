# ML Pipeline

Phase 7A labels describe transparent synthetic weather-rule outcomes. Phase 7C aligns predictors to target_date minus one day and keeps hazards in separate datasets with chronological train, validation, and test periods. Phases 7D, 7E, and 7F use those synthetic targets only.

Phase 7F compares eight candidates per hazard, including the five fixed baselines, the Phase 7E incumbent, tuned XGBoost, and tuned LightGBM. Candidate selection and threshold choice use validation data; the test evaluator is sealed and one-shot. Do not rerun scripts/evaluate_phase7f_final_test.py. Persisted outputs may be checked using scripts/validate_phase7f_final_test_report.py.

The same districts occur across temporal splits; unseen-district transfer is not tested. Scores are raw and uncalibrated. Metrics measure agreement with generated rules, not real disaster forecasting skill. No model is trained by Phase 9.
