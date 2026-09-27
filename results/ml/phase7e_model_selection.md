# Phase 7E Model Selection (Validation Only)

**SYNTHETIC_DEVELOPMENT_ONLY**

## Method

- Tuned the two strongest Phase 7D validation candidates per hazard; 20 deterministic randomized configurations per candidate.
- Hyperparameters were scored with three expanding date-block folds inside the training period. All districts from a target date stayed in the same fold.
- Final candidate comparison and threshold selection used the Phase 5 validation split only.
- Threshold grid: 0.10 through 0.90 by 0.10; select maximum F1, ties by precision, recall, then lower false-alert rate.
- Calibration: no post-hoc calibrator fitted; Brier score is reported for the uncalibrated estimator scores.
- At selection close, the final test split remained unread; the separate one-time evaluation report documents the subsequent held-out evaluation.
- These models reproduce synthetic weather-rule labels, not verified disaster events.

## Candidate results

| Hazard | Algorithm | CV AP (mean) | CV AP (SD) | Validation AP | Validation F1 at selected threshold | Selected threshold |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| coldwave | extra_trees | 0.0766 | 0.0436 | 0.0824 | 0.1553 | 0.10 |
| coldwave | random_forest (selected) | 0.0788 | 0.0471 | 0.0872 | 0.1553* | 0.10* |
| flood | hist_gradient_boosting (selected) | 0.1420 | 0.0560 | 0.0951 | 0.1905* | 0.10* |
| flood | random_forest | 0.1438 | 0.0220 | 0.0522 | 0.1905 | 0.10 |
| heatwave | extra_trees | 0.0808 | 0.0434 | 0.4511 | 0.4554 | 0.10 |
| heatwave | hist_gradient_boosting (selected) | 0.0785 | 0.0473 | 0.4571 | 0.4554* | 0.10* |
| heavy_rain | extra_trees (selected) | 0.2532 | 0.0255 | 0.1580 | 0.2226* | 0.10* |
| heavy_rain | logistic_regression | 0.2428 | 0.0243 | 0.1552 | 0.2226 | 0.10 |
| landslide | extra_trees (selected) | 0.0398 | 0.0259 | 0.0387 | 0.0000* | 0.10* |
| landslide | logistic_regression | 0.0292 | 0.0197 | 0.0279 | 0.0000 | 0.10 |
| windstorm | extra_trees | 0.0257 | 0.0119 | 0.0813 | 0.1317 | 0.40 |
| windstorm | random_forest (selected) | 0.0370 | 0.0196 | 0.0907 | 0.1317* | 0.40* |

`*` denotes the selected model and its validation-tuned threshold for that hazard. Threshold F1 is shown only on the selected candidate row.

## Selected model registry

- `flood`: `hist_gradient_boosting`, version `phase7e_v1`, threshold `0.10`, validation AP `0.0951`.
- `heavy_rain`: `extra_trees`, version `phase7e_v1`, threshold `0.10`, validation AP `0.1580`.
- `landslide`: `extra_trees`, version `phase7e_v1`, threshold `0.10`, validation AP `0.0387`.
- `heatwave`: `hist_gradient_boosting`, version `phase7e_v1`, threshold `0.10`, validation AP `0.4571`.
- `coldwave`: `random_forest`, version `phase7e_v1`, threshold `0.10`, validation AP `0.0872`.
- `windstorm`: `random_forest`, version `phase7e_v1`, threshold `0.40`, validation AP `0.0907`.

## Artifacts

- Final selected development models and metadata: `models/development/phase7e_selected/`.
- Candidate metrics: `results/ml/phase7e/candidate_validation_metrics.csv`.
- Trial checkpoint log: `results/ml/phase7e/temporal_cv_trials.jsonl`.
- Threshold analysis: `results/ml/phase7e/selected_threshold_analysis.csv`.
- Test evaluation is a separate, one-time next step after this selection report.
