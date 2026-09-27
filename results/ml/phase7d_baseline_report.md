# Phase 7D Baseline Training and Validation

**SYNTHETIC_DEVELOPMENT_ONLY**

## Result

All completed baseline artifacts and validation metrics were checked. Results measure how well models reproduce the Phase 7A synthetic weather-rule targets; they are not evidence of real disaster prediction skill.

- Baseline candidates: 30 across six hazards and five algorithms.
- Successful: 30; recorded failures: 0.
- Train data: Phase 5 `train` split only; validation data: Phase 5 `validation` split only.
- Test data: not read, evaluated, or used for selection. Test metrics are intentionally absent.
- `UNAVAILABLE` labels were already excluded in Phase 7C and were not recoded.
- Class imbalance: balanced class weights were used for Logistic Regression, Decision Tree, Random Forest, and Extra Trees; balanced per-row weights were used for HistGradientBoosting.
- Probability threshold: 0.50 for threshold metrics; PR-AUC is average precision and does not depend on that threshold.
- Model selection: no final champion or operating threshold is selected in this baseline phase.
- XGBoost and LightGBM: not run because neither was present in the available environment.
- No hyperparameter search or tuning was performed.

## Validation metrics

| Hazard | Algorithm | Train positives | Validation positives | Precision | Recall | F1 | PR-AUC | ROC-AUC | False-alert rate | Brier | Train seconds | Model bytes |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| coldwave | decision_tree | 316 | 155 | 0.0456 | 0.5548 | 0.0843 | 0.0356 | 0.6285 | 0.2518 | 0.1737 | 0.3 | 5,216 |
| coldwave | extra_trees | 316 | 155 | 0.1111 | 0.1548 | 0.1294 | 0.0781 | 0.8085 | 0.0269 | 0.0629 | 0.8 | 4,105,424 |
| coldwave | hist_gradient_boosting | 316 | 155 | 0.0739 | 0.2581 | 0.1149 | 0.0710 | 0.7979 | 0.0701 | 0.0595 | 6.3 | 149,481 |
| coldwave | logistic_regression | 316 | 155 | 0.0598 | 0.6452 | 0.1095 | 0.0696 | 0.7698 | 0.2199 | 0.1497 | 0.3 | 3,566 |
| coldwave | random_forest | 316 | 155 | 0.1000 | 0.0452 | 0.0622 | 0.0727 | 0.7974 | 0.0088 | 0.0357 | 2.1 | 1,966,228 |
| flood | decision_tree | 47 | 27 | 0.0384 | 0.6296 | 0.0723 | 0.0645 | 0.7934 | 0.0586 | 0.0518 | 0.2 | 2,714 |
| flood | extra_trees | 47 | 27 | 0.0938 | 0.1111 | 0.1017 | 0.0583 | 0.9191 | 0.0040 | 0.0074 | 0.5 | 1,043,552 |
| flood | hist_gradient_boosting | 47 | 27 | 0.2353 | 0.1481 | 0.1818 | 0.0943 | 0.8461 | 0.0018 | 0.0044 | 6.2 | 127,920 |
| flood | logistic_regression | 47 | 27 | 0.0296 | 0.3704 | 0.0548 | 0.0554 | 0.9000 | 0.0451 | 0.0355 | 0.4 | 3,568 |
| flood | random_forest | 47 | 27 | 0.2308 | 0.1111 | 0.1500 | 0.0966 | 0.8729 | 0.0014 | 0.0050 | 1.1 | 439,758 |
| heatwave | decision_tree | 349 | 712 | 0.2284 | 0.8020 | 0.3555 | 0.2619 | 0.7775 | 0.2928 | 0.1690 | 0.3 | 5,777 |
| heatwave | extra_trees | 349 | 712 | 0.3915 | 0.5829 | 0.4684 | 0.4539 | 0.8836 | 0.0979 | 0.0940 | 0.8 | 3,629,387 |
| heatwave | hist_gradient_boosting | 349 | 712 | 0.3772 | 0.4831 | 0.4236 | 0.4049 | 0.8680 | 0.0862 | 0.0861 | 6.3 | 148,232 |
| heatwave | logistic_regression | 349 | 712 | 0.2487 | 0.7795 | 0.3770 | 0.3504 | 0.8392 | 0.2546 | 0.1614 | 0.3 | 3,564 |
| heatwave | random_forest | 349 | 712 | 0.4882 | 0.1742 | 0.2567 | 0.3786 | 0.8680 | 0.0197 | 0.0728 | 2.0 | 1,957,087 |
| heavy_rain | decision_tree | 346 | 161 | 0.0800 | 0.5652 | 0.1402 | 0.0947 | 0.7352 | 0.1465 | 0.1107 | 0.3 | 6,750 |
| heavy_rain | extra_trees | 346 | 161 | 0.1510 | 0.4286 | 0.2233 | 0.1538 | 0.8694 | 0.0543 | 0.0580 | 0.8 | 3,423,029 |
| heavy_rain | hist_gradient_boosting | 346 | 161 | 0.1164 | 0.3354 | 0.1728 | 0.1296 | 0.8393 | 0.0574 | 0.0499 | 6.3 | 151,333 |
| heavy_rain | logistic_regression | 346 | 161 | 0.0934 | 0.6335 | 0.1628 | 0.1756 | 0.8337 | 0.1387 | 0.1155 | 0.4 | 3,568 |
| heavy_rain | random_forest | 346 | 161 | 0.2115 | 0.2733 | 0.2385 | 0.1414 | 0.8512 | 0.0230 | 0.0327 | 1.9 | 1,867,370 |
| landslide | decision_tree | 64 | 32 | 0.0139 | 0.2188 | 0.0262 | 0.0071 | 0.5760 | 0.0681 | 0.0619 | 0.2 | 3,221 |
| landslide | extra_trees | 64 | 32 | 0.0000 | 0.0000 | 0.0000 | 0.0349 | 0.8549 | 0.0021 | 0.0128 | 0.6 | 1,677,773 |
| landslide | hist_gradient_boosting | 64 | 32 | 0.0500 | 0.0312 | 0.0385 | 0.0185 | 0.7859 | 0.0026 | 0.0064 | 6.6 | 135,324 |
| landslide | logistic_regression | 64 | 32 | 0.0171 | 0.6250 | 0.0332 | 0.0249 | 0.8030 | 0.1586 | 0.1205 | 0.3 | 3,565 |
| landslide | random_forest | 64 | 32 | 0.0000 | 0.0000 | 0.0000 | 0.0203 | 0.8328 | 0.0039 | 0.0096 | 1.3 | 601,789 |
| windstorm | decision_tree | 121 | 156 | 0.0520 | 0.4423 | 0.0931 | 0.0441 | 0.6482 | 0.1761 | 0.1289 | 0.3 | 5,098 |
| windstorm | extra_trees | 121 | 156 | 0.1515 | 0.0321 | 0.0529 | 0.0789 | 0.7996 | 0.0039 | 0.0395 | 0.8 | 2,537,125 |
| windstorm | hist_gradient_boosting | 121 | 156 | 0.1408 | 0.0641 | 0.0881 | 0.0771 | 0.7440 | 0.0085 | 0.0263 | 6.3 | 147,183 |
| windstorm | logistic_regression | 121 | 156 | 0.0524 | 0.5833 | 0.0961 | 0.0672 | 0.7679 | 0.2304 | 0.1644 | 0.4 | 3,567 |
| windstorm | random_forest | 121 | 156 | 1.0000 | 0.0064 | 0.0127 | 0.0777 | 0.7665 | 0.0000 | 0.0225 | 1.8 | 1,237,042 |

## Artifacts

- Metrics: `results/ml/phase7d_baseline_validation_metrics.csv`.
- Experiment log: `results/ml/phase7d_baseline_experiment_log.jsonl`.
- Models and per-model metadata: `models/development/phase7d/`.
- Validation script: `scripts/validate_phase7d_baselines.py`.
- Algorithms: Logistic Regression, Decision Tree, Random Forest, Extra Trees, HistGradientBoosting.
- Metrics include precision, recall, F1, average precision (PR-AUC), ROC-AUC, Brier score, confusion counts, false-alert rate, fit time, and serialized model size.
