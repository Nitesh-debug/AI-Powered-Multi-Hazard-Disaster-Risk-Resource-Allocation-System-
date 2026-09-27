# Phase 7E Final Test Evaluation

**SYNTHETIC_DEVELOPMENT_ONLY**

One-time evaluation completed at `2026-09-25T18:45:24.240135+00:00`. The final chronological test rows were read once; no threshold, model, or feature selection was changed from test results.

These measures quantify reproduction of the synthetic Phase 7A rules only. They are not evidence of real-world hazard prediction skill, operational calibration, or verified disaster detection.

## Overall Test Results

| Hazard | Rows | Positives | Threshold (validation) | AP | ROC-AUC | Precision | Recall | F1 | False-alert rate | Brier |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| flood | 20700 | 92 | 0.10 | 0.0596 | 0.8329 | 0.0870 | 0.0435 | 0.0580 | 0.0020 | 0.0048 |
| heavy_rain | 20700 | 624 | 0.10 | 0.2040 | 0.8679 | 0.1931 | 0.4391 | 0.2682 | 0.0570 | 0.0263 |
| landslide | 20700 | 81 | 0.10 | 0.0198 | 0.8586 | 0.0000 | 0.0000 | 0.0000 | 0.0002 | 0.0039 |
| heatwave | 20700 | 2958 | 0.10 | 0.4036 | 0.7998 | 0.4736 | 0.2786 | 0.3508 | 0.0516 | 0.1222 |
| coldwave | 20700 | 1491 | 0.10 | 0.2176 | 0.7704 | 0.3087 | 0.1737 | 0.2223 | 0.0302 | 0.0652 |
| windstorm | 20700 | 367 | 0.40 | 0.0472 | 0.6855 | 0.0494 | 0.2071 | 0.0797 | 0.0720 | 0.0575 |

District and seasonal metrics are in `results/ml/phase7e/final_test_metrics.csv`. Metrics are suppressed when a subgroup has fewer than 5 positives or negatives; subgroup sample sizes are retained.

All labels remain synthetic; the reported scores must not be used for real alerts, public risk communication, or resource dispatch.
