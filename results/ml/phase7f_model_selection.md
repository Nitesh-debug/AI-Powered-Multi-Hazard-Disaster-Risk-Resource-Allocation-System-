# Phase 7F v1 Model Selection (Validation Only)

**SYNTHETIC_DEVELOPMENT_ONLY**

This is a new versioned experiment. Existing Phase 7D, Phase 7D XGBoost/LightGBM, and Phase 7E reports/artifacts are preserved.

## Method

- All data loading uses the Phase 7D hash-checked train/validation-prefix loader; test rows are not loaded during tuning or selection.
- Five Phase 7D algorithms are refit with their existing baseline configurations. The Phase 7E selected incumbent is also refit with its frozen parameters for each hazard.
- XGBoost and LightGBM each receive 20 deterministic randomized configurations per hazard; configurations are scored with 3 expanding target-date folds inside training.
- Entire district-date cohorts remain in the same temporal fold. `scale_pos_weight` is computed from each fitting fold (or the train split for final candidate fit), never from validation/test labels.
- The candidate comparison metric is validation average precision. ROC-AUC, false-alarm rate at 0.50, then candidate ID are deterministic tie-breakers.
- The eight candidates are five fixed Phase 7D baselines, one Phase 7E selected incumbent refit, and tuned XGBoost and LightGBM. Prior Phase 7D/7E validation metrics are retained as references; the Phase 7F comparison uses fresh fits on the same train/validation splits.
- Temporal evaluation retains the same 20 districts in later periods. Spatial transfer to unseen districts is not tested; correlated district weather can still limit generalization.
- The same chronological test interval was already evaluated for Phase 7E in an earlier version. Phase 7F will not use those prior test metrics for selection, but its evaluation is not a project-wide pristine holdout.
- Thresholds are selected on validation only by maximum F1 over 0.10 through 0.90. No calibration is fitted; estimator scores remain raw and uncalibrated.
- Every candidate is SYNTHETIC_DEVELOPMENT_ONLY (`phase7a_v1`); these experiments do not measure verified disaster forecasting skill.

## Candidate Results

| Hazard | Candidate | Algorithm | Prior AP reference | CV AP mean (SD) | Phase 7F validation AP | ROC-AUC | F1 at 0.50 | FAR at 0.50 | Fit seconds | Selected |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| coldwave | phase7d_decision_tree | decision_tree | 0.0356 | not tuned | 0.0356 | 0.6285 | 0.0843 | 0.2518 | 0.42 | no |
| coldwave | phase7d_extra_trees | extra_trees | 0.0781 | not tuned | 0.0781 | 0.8085 | 0.1294 | 0.0269 | 0.97 | no |
| coldwave | phase7d_hist_gradient_boosting | hist_gradient_boosting | 0.0710 | not tuned | 0.0908 | 0.8141 | 0.0240 | 0.0014 | 0.70 | YES |
| coldwave | phase7d_logistic_regression | logistic_regression | 0.0696 | not tuned | 0.0697 | 0.7701 | 0.1093 | 0.2204 | 0.42 | no |
| coldwave | phase7d_random_forest | random_forest | 0.0727 | not tuned | 0.0702 | 0.7996 | 0.0533 | 0.0090 | 2.74 | no |
| coldwave | phase7e_incumbent_refit | random_forest | 0.0872 | not tuned | 0.0872 | 0.7907 | 0.0000 | 0.0000 | 2.96 | no |
| coldwave | phase7f_tuned_lightgbm | lightgbm | 0.0673 | 0.0616 (0.0285) | 0.0881 | 0.8044 | 0.1228 | 0.0981 | 0.87 | no |
| coldwave | phase7f_tuned_xgboost | xgboost | 0.0736 | 0.0644 (0.0334) | 0.0826 | 0.8055 | 0.1275 | 0.1510 | 0.72 | no |
| flood | phase7d_decision_tree | decision_tree | 0.0645 | not tuned | 0.0645 | 0.7934 | 0.0723 | 0.0586 | 0.34 | no |
| flood | phase7d_extra_trees | extra_trees | 0.0583 | not tuned | 0.0583 | 0.9191 | 0.1017 | 0.0040 | 0.72 | no |
| flood | phase7d_hist_gradient_boosting | hist_gradient_boosting | 0.0943 | not tuned | 0.0916 | 0.8587 | 0.0000 | 0.0001 | 1.93 | no |
| flood | phase7d_logistic_regression | logistic_regression | 0.0554 | not tuned | 0.0542 | 0.8998 | 0.0548 | 0.0451 | 0.44 | no |
| flood | phase7d_random_forest | random_forest | 0.0966 | not tuned | 0.0909 | 0.8741 | 0.1538 | 0.0012 | 2.15 | no |
| flood | phase7e_incumbent_refit | hist_gradient_boosting | 0.0951 | not tuned | 0.0726 | 0.7771 | 0.0625 | 0.0005 | 0.79 | no |
| flood | phase7f_tuned_lightgbm | lightgbm | 0.0453 | 0.1093 (0.0564) | 0.0648 | 0.8436 | 0.1364 | 0.0019 | 1.34 | no |
| flood | phase7f_tuned_xgboost | xgboost | 0.1017 | 0.1481 (0.0265) | 0.1071 | 0.7849 | 0.1667 | 0.0023 | 2.02 | YES |
| heatwave | phase7d_decision_tree | decision_tree | 0.2619 | not tuned | 0.2619 | 0.7775 | 0.3555 | 0.2928 | 0.61 | no |
| heatwave | phase7d_extra_trees | extra_trees | 0.4539 | not tuned | 0.4539 | 0.8836 | 0.4684 | 0.0979 | 0.87 | YES |
| heatwave | phase7d_hist_gradient_boosting | hist_gradient_boosting | 0.4049 | not tuned | 0.4128 | 0.8741 | 0.0988 | 0.0029 | 0.60 | no |
| heatwave | phase7d_logistic_regression | logistic_regression | 0.3504 | not tuned | 0.3499 | 0.8389 | 0.3768 | 0.2549 | 0.75 | no |
| heatwave | phase7d_random_forest | random_forest | 0.3786 | not tuned | 0.3757 | 0.8670 | 0.2479 | 0.0206 | 3.31 | no |
| heatwave | phase7e_incumbent_refit | hist_gradient_boosting | 0.4571 | not tuned | 0.4385 | 0.8820 | 0.0381 | 0.0012 | 0.23 | no |
| heatwave | phase7f_tuned_lightgbm | lightgbm | 0.4232 | 0.0718 (0.0554) | 0.3964 | 0.8506 | 0.3000 | 0.0184 | 1.60 | no |
| heatwave | phase7f_tuned_xgboost | xgboost | 0.4317 | 0.0723 (0.0421) | 0.4182 | 0.8814 | 0.4594 | 0.1179 | 1.80 | no |
| heavy_rain | phase7d_decision_tree | decision_tree | 0.0947 | not tuned | 0.0947 | 0.7352 | 0.1402 | 0.1465 | 0.59 | no |
| heavy_rain | phase7d_extra_trees | extra_trees | 0.1538 | not tuned | 0.1538 | 0.8694 | 0.2233 | 0.0543 | 0.77 | no |
| heavy_rain | phase7d_hist_gradient_boosting | hist_gradient_boosting | 0.1296 | not tuned | 0.1345 | 0.8464 | 0.0449 | 0.0018 | 0.55 | no |
| heavy_rain | phase7d_logistic_regression | logistic_regression | 0.1756 | not tuned | 0.1761 | 0.8338 | 0.1631 | 0.1384 | 0.59 | YES |
| heavy_rain | phase7d_random_forest | random_forest | 0.1414 | not tuned | 0.1432 | 0.8507 | 0.2343 | 0.0228 | 2.83 | no |
| heavy_rain | phase7e_incumbent_refit | extra_trees | 0.1580 | not tuned | 0.1580 | 0.8556 | 0.0479 | 0.0003 | 1.98 | no |
| heavy_rain | phase7f_tuned_lightgbm | lightgbm | 0.1251 | 0.2301 (0.0259) | 0.1393 | 0.8374 | 0.2063 | 0.0688 | 2.63 | no |
| heavy_rain | phase7f_tuned_xgboost | xgboost | 0.1196 | 0.2172 (0.0333) | 0.1565 | 0.8704 | 0.1521 | 0.1969 | 0.49 | no |
| landslide | phase7d_decision_tree | decision_tree | 0.0071 | not tuned | 0.0071 | 0.5760 | 0.0262 | 0.0681 | 0.28 | no |
| landslide | phase7d_extra_trees | extra_trees | 0.0349 | not tuned | 0.0349 | 0.8549 | 0.0000 | 0.0021 | 0.69 | no |
| landslide | phase7d_hist_gradient_boosting | hist_gradient_boosting | 0.0185 | not tuned | 0.0222 | 0.8308 | 0.0000 | 0.0001 | 0.59 | no |
| landslide | phase7d_logistic_regression | logistic_regression | 0.0249 | not tuned | 0.0250 | 0.8035 | 0.0331 | 0.1592 | 0.42 | no |
| landslide | phase7d_random_forest | random_forest | 0.0203 | not tuned | 0.0199 | 0.8296 | 0.0000 | 0.0043 | 1.74 | no |
| landslide | phase7e_incumbent_refit | extra_trees | 0.0387 | not tuned | 0.0387 | 0.8959 | 0.0000 | 0.0000 | 0.93 | YES |
| landslide | phase7f_tuned_lightgbm | lightgbm | 0.0233 | 0.0333 (0.0148) | 0.0106 | 0.6232 | 0.0290 | 0.0050 | 1.49 | no |
| landslide | phase7f_tuned_xgboost | xgboost | 0.0184 | 0.0337 (0.0258) | 0.0127 | 0.7323 | 0.0000 | 0.0022 | 2.18 | no |
| windstorm | phase7d_decision_tree | decision_tree | 0.0441 | not tuned | 0.0441 | 0.6482 | 0.0931 | 0.1761 | 0.39 | no |
| windstorm | phase7d_extra_trees | extra_trees | 0.0789 | not tuned | 0.0789 | 0.7996 | 0.0529 | 0.0039 | 0.79 | no |
| windstorm | phase7d_hist_gradient_boosting | hist_gradient_boosting | 0.0771 | not tuned | 0.0765 | 0.7703 | 0.0127 | 0.0000 | 0.51 | no |
| windstorm | phase7d_logistic_regression | logistic_regression | 0.0672 | not tuned | 0.0672 | 0.7676 | 0.0962 | 0.2303 | 0.37 | no |
| windstorm | phase7d_random_forest | random_forest | 0.0777 | not tuned | 0.0780 | 0.7590 | 0.0127 | 0.0001 | 2.34 | no |
| windstorm | phase7e_incumbent_refit | random_forest | 0.0907 | not tuned | 0.0878 | 0.8022 | 0.0670 | 0.0024 | 2.00 | YES |
| windstorm | phase7f_tuned_lightgbm | lightgbm | 0.0575 | 0.0300 (0.0320) | 0.0654 | 0.7102 | 0.0235 | 0.0017 | 2.46 | no |
| windstorm | phase7f_tuned_xgboost | xgboost | 0.0687 | 0.0425 (0.0238) | 0.0737 | 0.7932 | 0.1218 | 0.1702 | 0.51 | no |

## Selected Validation Operating Points

| Hazard | Selected candidate | Threshold | Precision | Recall | F1 | FAR | AP | ROC-AUC | Brier |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| flood | phase7f_tuned_xgboost | 0.30 | 0.1818 | 0.2222 | 0.2000 | 0.0037 | 0.1071 | 0.7849 | 0.0048 |
| heavy_rain | phase7d_logistic_regression | 0.80 | 0.1792 | 0.3540 | 0.2380 | 0.0366 | 0.1761 | 0.8338 | 0.1154 |
| landslide | phase7e_incumbent_refit | 0.10 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0387 | 0.8959 | 0.0043 |
| heatwave | phase7d_extra_trees | 0.50 | 0.3915 | 0.5829 | 0.4684 | 0.0979 | 0.4539 | 0.8836 | 0.0940 |
| coldwave | phase7d_hist_gradient_boosting | 0.10 | 0.1055 | 0.1871 | 0.1349 | 0.0344 | 0.0908 | 0.8141 | 0.0207 |
| windstorm | phase7e_incumbent_refit | 0.20 | 0.0746 | 0.3654 | 0.1239 | 0.0990 | 0.0878 | 0.8022 | 0.0293 |

## Artifacts

- Trial configurations and fold scores: `results/ml/phase7f/xgb_lgbm_temporal_cv_trials.jsonl`.
- All candidate metrics: `results/ml/phase7f/candidate_validation_metrics.csv`.
- Selected validation threshold analysis: `results/ml/phase7f/selected_threshold_analysis.csv`.
- Versioned model registry: `models/development/phase7f_selected/`.
- Test rows read: **No**. Final test evaluation is a separate one-time command after this selection is frozen.
