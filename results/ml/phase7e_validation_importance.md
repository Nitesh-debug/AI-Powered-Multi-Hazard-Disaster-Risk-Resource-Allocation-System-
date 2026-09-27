# Phase 7E Validation-Only Feature Importance

**SYNTHETIC_DEVELOPMENT_ONLY**

Permutation importance uses 3 repeats and average-precision decrease on the Phase 5 validation rows only. The final test split was not loaded.

This describes which weather predictors help each selected model reproduce the Phase 7A rules. It is not causal attribution or evidence about real hazards.

| Hazard | Top validation feature | Mean AP decrease | Validation AP |
| --- | --- | ---: | ---: |
| flood | `rain_7d_end_of_day` | 0.06025 | 0.0951 |
| heavy_rain | `rain_3h_end_of_day` | 0.04682 | 0.1580 |
| landslide | `rain_12h_end_of_day` | 0.00391 | 0.0387 |
| heatwave | `temperature_2m_daily_max` | 0.26907 | 0.4571 |
| coldwave | `soil_temperature_28_100cm_mean_24h_daily_mean` | 0.02487 | 0.0872 |
| windstorm | `wind_gusts_10m_daily_max` | 0.00956 | 0.0907 |

Full feature-level results: `results/ml/phase7e/validation_permutation_importance.csv`.
