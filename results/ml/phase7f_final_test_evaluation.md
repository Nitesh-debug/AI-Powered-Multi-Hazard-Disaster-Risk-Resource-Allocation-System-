# Phase 7F v1 Final Test Evaluation

**SYNTHETIC_DEVELOPMENT_ONLY**

One-time evaluation completed at `2026-09-27T07:52:15.031871+00:00`. The 20,700-row chronological test split per hazard was read after model and threshold selection were frozen.

Scores assess reproduction of synthetic Phase 7A rules only. They are not real-world disaster forecasting accuracy, calibrated probabilities, or evidence for operational warning or dispatch.

The same chronological interval was already evaluated once by Phase 7E. These Phase 7F results were not used for tuning or selection, but this interval is not an independent project-wide pristine holdout.

## Overall Results

| Hazard | Rows | Positive | Negative | Validation threshold | AP | ROC-AUC | Precision | Recall | F1 | FAR | Raw-score Brier diagnostic |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| flood | 20700 | 92 | 20608 | 0.30 | 0.0592 | 0.8455 | 0.1157 | 0.1522 | 0.1315 | 0.0052 | 0.0059 |
| heavy_rain | 20700 | 624 | 20076 | 0.80 | 0.2063 | 0.8417 | 0.2185 | 0.4199 | 0.2874 | 0.0467 | 0.1266 |
| landslide | 20700 | 81 | 20619 | 0.10 | 0.0198 | 0.8586 | 0.0000 | 0.0000 | 0.0000 | 0.0002 | 0.0039 |
| heatwave | 20700 | 2958 | 17742 | 0.50 | 0.3811 | 0.7732 | 0.4148 | 0.3908 | 0.4024 | 0.0919 | 0.1219 |
| coldwave | 20700 | 1491 | 19209 | 0.10 | 0.1843 | 0.7603 | 0.2486 | 0.0892 | 0.1313 | 0.0209 | 0.0682 |
| windstorm | 20700 | 367 | 20333 | 0.20 | 0.0439 | 0.6918 | 0.0409 | 0.2807 | 0.0714 | 0.1188 | 0.0307 |

District/season records are in `results/ml/phase7f/final_test_metrics.csv`. Subgroup metrics are withheld below 5 positives or negatives; subgroup support counts remain visible.

Selected models, feature contracts, thresholds, and model hashes are unchanged. The registry metadata records this evaluation as completed once.
