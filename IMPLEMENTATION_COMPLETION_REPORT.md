# JK Disaster Management System: Implementation and Validation Report

**Report date:** 2026-09-26
**Project:** Jammu & Kashmir multi-hazard disaster-management development system
**Scope:** Review of the current project artifacts and implementation record through Phases 1-8, including development API/UI work. This report summarizes saved validation and evaluation artifacts. It does not rerun the one-time test evaluation.

## Executive Summary

The project now contains a historical district weather panel, engineered weather features, a source-audited disaster-label track, six separate synthetic development targets, chronological model-development artifacts, and a local FastAPI/React/Leaflet demonstration with replay and live-weather modes.

The most important scientific limitation remains unresolved: the historical flood inventory contains **32 verified positive district-days and 0 verified negative district-days**. The other five hazards have **0 accepted verified project-period event labels** in the Phase 4 assessment. `NO_VERIFIED_EVENT` remains unknown, not a negative. Accordingly, model results below measure reproduction of transparent synthetic weather rules, not real disaster prediction. Do not use the scores for public warnings, operational decisions, or dispatch.

The local development console and service scaffolding are present. A production deployment is **not** complete: the project has no connected Supabase account, authentication, verified operational inventory, public deployment, or completed Docker image build in the current environment.

## Phase Status

| Phase / capability | Status | What exists |
| --- | --- | --- |
| 1. Historical weather collection | Complete | Open-Meteo Archive API hourly weather for 20 selected district points, 2020-01-01 through 2025-10-31. |
| 2. Weather merging | Complete | Validated district files merged into one 1,022,880-row hourly panel. |
| 3. Weather feature engineering | Complete | Past-looking rolling, lag, daily and calendar/weather features; 68 shifted predictors selected for the one-day-ahead contract. |
| 4. Disaster-data assessment | Complete as assessment | Verified flood positives are retained; other hazard-source limitations and the unknown-label problem are documented. |
| 5. ML dataset design | Complete as design | One-day-ahead target contract and chronological split plan; no real-label binary dataset is ready. |
| 6. Label/source coverage | Preparation complete | Negative-label requirements and a source-coverage matrix were documented. Auditable verified no-flood coverage was not established. |
| 7. Synthetic development | Complete for development experiments | Six `phase7a_v1` synthetic labels, separate model-ready data, 30 baselines, 12 tuned candidates, six selected models and a one-time synthetic test evaluation. |
| 8. Weather pipeline / local demo | Implemented for development | Label-free historical replay, Open-Meteo ECMWF live adapter, API/UI, local persistence, signal display and bounded simulated allocations. |
| 9. FastAPI | Implemented locally | API routes exist and have focused tests. No production deployment. |
| 10. Supabase | Scaffolded, not connected | Development-only SQL schema with RLS and no public/anonymous policies; SQLite remains active. No user Supabase credentials configured. |
| 11. React + Leaflet | Implemented locally | React/Vite console and source weather-reference point map. District boundary polygons are not inferred. |
| 12. Alerts / resource allocation | Simulation only | Local development signals and fixed demo inventory; outbound messages and real dispatch are disabled. |
| 13. Testing | Partial / environment-dependent | Saved phase validations and previous test/build passes are recorded below. Current Python rerun was unavailable; Docker build was not run. |
| 14. Deployment | Not complete | Compose and CI definitions exist, but no production deployment or security approval is recorded. |

## Weather Data and Feature Engineering

- **Historical source:** Open-Meteo Archive API (`archive-api.open-meteo.com/v1/archive`). The collection script requests 15 hourly weather variables, with latitude, longitude, district and timestamp.
- **Districts:** 20. The list is Anantnag, Bandipora, Baramulla, Budgam, Doda, Ganderbal, Jammu, Kathua, Kishtwar, Kulgam, Kupwara, Poonch, Pulwama, Rajouri, Ramban, Reasi, Samba, Shopian, Srinagar and Udhampur. Leh and Kargil are explicitly excluded from this selected panel.
- **Coverage:** 2020-01-01 00:00 through 2025-10-31 23:00; **51,144 hourly rows per district**, **1,022,880 rows total**.
- **Input validation record:** 20 district-file rows plus one summary row in `results/weather_validation_report.csv`; all report `PASS`. Duplicate rows, duplicate timestamps and missing cells: **0** in the validated raw hourly files. Expected date range and coordinate checks pass for all 20 districts.
- **Feature families:** rolling precipitation/rain (3h, 6h, 12h, 24h, 3d, 7d), snowfall, temperature/humidity/wind summaries, gusts, soil moisture and temperature summaries, 24-hour lags/changes, calendar values and cyclical encodings. Rolling/lag warm-up gaps are retained as missing rather than silently treated as observed zeroes.
- **Prediction contract:** use the 68 Phase 5 shifted daily weather predictors from `feature_reference_date` to predict the next `target_date`. District and date are keys; label/provenance fields are not predictors. Static coordinates are not part of the frozen 68-feature predictor contract.
- **Processed-data protection:** historical weather, engineered weather and existing flood data remain source artifacts. Synthetic outputs are stored separately under `data/development/`.

## Historical Disaster Labels and Evidence Limits

### Flood

The curated flood pipeline retained **29 explicit IFI records**, normalized into **32 verified district-date combinations** across **15 of 20 districts**. The verified-positive date range is **2020-04-27 to 2023-08-18**. Three event IDs span two districts each, so 32 district-days are not 32 independent flood episodes. The label evidence comes from one IMD-labelled source and one source URL in the current daily artifact.

The daily flood panel has **42,620 district-days**: **32 `VERIFIED_FLOOD` positives**, **42,588 `NO_VERIFIED_EVENT` unknowns**, and **0 confirmed negatives**. There are no duplicate district-date rows. The 42,588 unknowns are not non-events. The verified positives stop in August 2023 even though weather coverage continues to 2025-10-31.

Phase 5's planned split counts for the verified flood panel are:

| Split | Target dates | Rows | Verified positives | Unknown | Confirmed negatives |
| --- | --- | ---: | ---: | ---: | ---: |
| Train | 2020-01-02 to 2021-12-31 | 14,600 | 17 | 14,583 | 0 |
| Validation | 2022-01-01 to 2022-12-31 | 7,300 | 8 | 7,292 | 0 |
| Test | 2023-01-01 to 2025-10-31 | 20,700 | 7 | 20,693 | 0 |

The flood training/validation/test splits contain respectively **14, 8 and 7 unique event IDs**. The seven test event IDs are all in 2023; 2024-2025 cannot be considered negative. The 68 candidate weather predictors are large relative to the number of independent event episodes. Conventional supervised binary flood training and valid negative-based evaluation are therefore not supported by these historical labels.

### Other hazards

The Phase 4 accepted project-period event inventory has **0** landslide, heatwave, coldwave, windstorm and heavy-rain event labels. Specific gaps documented:

- **Landslide:** 11,033 NASA catalog records inspected, including 201 within the J&K bounding box; no accepted event was in the 2020-2025 target period. No coordinate-to-district guesses were made.
- **Heatwave:** no verified project-period events; station maxima, normals, terrain/region classification and official event/criteria evidence are missing.
- **Coldwave:** no verified project-period events; station minima, normals, regional/terrain handling and official event evidence are missing.
- **Windstorm:** no accepted event records or dates. 15 NOAA stations were identified in the J&K bounding area, but observations are not event labels and a project-approved windstorm taxonomy/criterion is absent.
- **Heavy rain:** no accepted event labels. IMD 24-hour intensity categories are documented as heavy **64.5-115.5 mm**, very heavy **115.6-204.4 mm**, and extremely heavy **204.5 mm or more**; these are intensity categories, not automatically disaster-event labels.

### Negative-label source audit

The Phase 6 matrix records the India Flood Inventory as a positive event catalogue with partial district coverage, dated records, no explicit nil reporting and unknown completeness; it cannot establish verified no-flood days. Static IIT Delhi district aggregates do not have event dates. IMD rainfall, NOAA precipitation, NASA GPM and Copernicus ERA5-Land are weather observations/estimates, not flood occurrence or non-occurrence records. JKSDMA and some IMD source coverage/completeness fields remain `UNKNOWN`. Candidate control-room logs, situation reports and incident registers are source classes only; no specific complete archive or nil-reporting protocol was verified.

The defensible next label source must have a fixed flood taxonomy and district-date unit, traceable positive incidents, explicit nil reports or demonstrably complete daily surveillance, coverage dates and districts, reporting cadence, missing-report handling, reporting delays/corrections, and auditable provenance. Until then, retain three states: `VERIFIED_FLOOD`, `VERIFIED_NO_FLOOD`, and `UNKNOWN`. Weather thresholds, quiet weather, missing news and absent catalogue records are not confirmed negatives.

## Synthetic Development Labels and Model-Ready Data

All labels below are **`SYNTHETIC_DEVELOPMENT_ONLY`**, rule version **`phase7a_v1`**. They describe weather-rule triggers and do not assert a real event occurred or did not occur. Relative thresholds are fitted on the Phase 5 train target period, 2020-01-02 through 2021-12-31, and frozen. Threshold strata are district-season for rain, soil moisture and wind, and district-calendar-month for temperature; rain percentiles use positive-rain days; threshold support requires at least 30 valid daily observations, with documented fallback or `UNAVAILABLE`. Target-date weather generates the synthetic target but is excluded from the one-day-ahead predictors.

| Synthetic target | Documented rule in brief | Phase 7B positive | Phase 7B zero | Phase 7B unavailable | Phase 7C usable positive | Phase 7C usable negative |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `synthetic_flood_dev_v1` | Target-day 24h rain > 0 and >= Q95, 7d rain >= Q90, deep soil moisture >= Q90. | 166 | 42,334 | 120 | 166 | 42,314 |
| `synthetic_heavy_rain_dev_v1` | Target-day 24h rain > 0 and >= district-season Q95. | 1,132 | 41,488 | 0 | 1,131 | 41,349 |
| `synthetic_landslide_dev_v1` | 3d rain >= Q95, shallow soil moisture >= Q90, positive 24h soil-moisture change >= Q90. | 177 | 42,403 | 40 | 177 | 42,303 |
| `synthetic_heatwave_dev_v1` | Daily max temperature >= district-month Q95 on two consecutive days. | 4,019 | 38,581 | 20 | 4,019 | 38,461 |
| `synthetic_coldwave_dev_v1` | Daily min temperature <= district-month Q05 on two consecutive days. | 1,962 | 40,638 | 20 | 1,962 | 40,518 |
| `synthetic_windstorm_dev_v1` | Gust max >= district-season Q99 and wind max >= Q95. | 644 | 41,976 | 0 | 644 | 41,836 |

Phase 7B label artifact: **42,620 rows**, **20 districts**, 2020-01-01 to 2025-10-31. Every row carries the synthetic scope and rule version. Missing rule input/threshold means `UNAVAILABLE`, not zero.

Phase 7C prepared six separate datasets. Each has **42,480 usable rows**, **20 districts**, **68 predictors**, and target dates 2020-01-08 to 2025-10-31. The row reduction of **140** from the 42,620 label rows includes out-of-split dates and rows without a complete prior-day feature vector; it is not the unavailable count alone. Every hazard is retained separately.

| Target | Total positives | Total negatives | Unavailable in Phase 7B | Train rows / positives | Validation rows / positives | Test rows / positives |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Flood-like | 166 | 42,314 | 120 | 14,480 / 47 | 7,300 / 27 | 20,700 / 92 |
| Heavy-rain-like | 1,131 | 41,349 | 0 | 14,480 / 346 | 7,300 / 161 | 20,700 / 624 |
| Landslide-condition-like | 177 | 42,303 | 40 | 14,480 / 64 | 7,300 / 32 | 20,700 / 81 |
| Heat-like | 4,019 | 38,461 | 20 | 14,480 / 349 | 7,300 / 712 | 20,700 / 2,958 |
| Cold-like | 1,962 | 40,518 | 20 | 14,480 / 316 | 7,300 / 155 | 20,700 / 1,491 |
| Wind-like | 644 | 41,836 | 0 | 14,480 / 121 | 7,300 / 156 | 20,700 / 367 |

All six splits preserve all **20 districts**. Dates are chronological, not randomly split by district-day. Train target dates are 2020-01-08 to 2021-12-31, validation 2022-01-01 to 2022-12-31, and test 2023-01-01 to 2025-10-31. Predictors are reconstructed from `feature_reference_date = target_date - 1 day`; target-date weather, label columns and verified-label provenance are excluded. The synthetic positive/negative counts in these tables are **not** verified disaster examples.

## Model Development and Results

### Phase 7D baselines

Five algorithms were fit for each of six synthetic targets: Logistic Regression, Decision Tree, Random Forest, Extra Trees and HistGradientBoosting. This is **30/30 successful baseline candidates, 0 failures**. Training used the Phase 5 train split and metrics used validation only; the test split was not read in this phase. Threshold metrics use probability cutoff **0.50**. Class weights were balanced for the four named classifiers and balanced per-row weights were used for HistGradientBoosting. XGBoost and LightGBM were not run; no tuning was performed in Phase 7D.

The full saved Phase 7D validation metrics are transcribed below. `P`=precision, `R`=recall, `AP`=average precision/PR-AUC, `ROC`=ROC-AUC, `FAR`=false-alert rate. Runtime is recorded fit seconds; size is serialized model bytes.

| Hazard | Algorithm | P | R | F1 | AP | ROC | FAR | Brier | Fit s | Bytes |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| coldwave | decision_tree | 0.0456 | 0.5548 | 0.0843 | 0.0356 | 0.6285 | 0.2518 | 0.1737 | 0.3 | 5,216 |
| coldwave | extra_trees | 0.1111 | 0.1548 | 0.1294 | 0.0781 | 0.8085 | 0.0269 | 0.0629 | 0.8 | 4,105,424 |
| coldwave | hist_gradient_boosting | 0.0739 | 0.2581 | 0.1149 | 0.0710 | 0.7979 | 0.0701 | 0.0595 | 6.3 | 149,481 |
| coldwave | logistic_regression | 0.0598 | 0.6452 | 0.1095 | 0.0696 | 0.7698 | 0.2199 | 0.1497 | 0.3 | 3,566 |
| coldwave | random_forest | 0.1000 | 0.0452 | 0.0622 | 0.0727 | 0.7974 | 0.0088 | 0.0357 | 2.1 | 1,966,228 |
| flood | decision_tree | 0.0384 | 0.6296 | 0.0723 | 0.0645 | 0.7934 | 0.0586 | 0.0518 | 0.2 | 2,714 |
| flood | extra_trees | 0.0938 | 0.1111 | 0.1017 | 0.0583 | 0.9191 | 0.0040 | 0.0074 | 0.5 | 1,043,552 |
| flood | hist_gradient_boosting | 0.2353 | 0.1481 | 0.1818 | 0.0943 | 0.8461 | 0.0018 | 0.0044 | 6.2 | 127,920 |
| flood | logistic_regression | 0.0296 | 0.3704 | 0.0548 | 0.0554 | 0.9000 | 0.0451 | 0.0355 | 0.4 | 3,568 |
| flood | random_forest | 0.2308 | 0.1111 | 0.1500 | 0.0966 | 0.8729 | 0.0014 | 0.0050 | 1.1 | 439,758 |
| heatwave | decision_tree | 0.2284 | 0.8020 | 0.3555 | 0.2619 | 0.7775 | 0.2928 | 0.1690 | 0.3 | 5,777 |
| heatwave | extra_trees | 0.3915 | 0.5829 | 0.4684 | 0.4539 | 0.8836 | 0.0979 | 0.0940 | 0.8 | 3,629,387 |
| heatwave | hist_gradient_boosting | 0.3772 | 0.4831 | 0.4236 | 0.4049 | 0.8680 | 0.0862 | 0.0861 | 6.3 | 148,232 |
| heatwave | logistic_regression | 0.2487 | 0.7795 | 0.3770 | 0.3504 | 0.8392 | 0.2546 | 0.1614 | 0.3 | 3,564 |
| heatwave | random_forest | 0.4882 | 0.1742 | 0.2567 | 0.3786 | 0.8680 | 0.0197 | 0.0728 | 2.0 | 1,957,087 |
| heavy_rain | decision_tree | 0.0800 | 0.5652 | 0.1402 | 0.0947 | 0.7352 | 0.1465 | 0.1107 | 0.3 | 6,750 |
| heavy_rain | extra_trees | 0.1510 | 0.4286 | 0.2233 | 0.1538 | 0.8694 | 0.0543 | 0.0580 | 0.8 | 3,423,029 |
| heavy_rain | hist_gradient_boosting | 0.1164 | 0.3354 | 0.1728 | 0.1296 | 0.8393 | 0.0574 | 0.0499 | 6.3 | 151,333 |
| heavy_rain | logistic_regression | 0.0934 | 0.6335 | 0.1628 | 0.1756 | 0.8337 | 0.1387 | 0.1155 | 0.4 | 3,568 |
| heavy_rain | random_forest | 0.2115 | 0.2733 | 0.2385 | 0.1414 | 0.8512 | 0.0230 | 0.0327 | 1.9 | 1,867,370 |
| landslide | decision_tree | 0.0139 | 0.2188 | 0.0262 | 0.0071 | 0.5760 | 0.0681 | 0.0619 | 0.2 | 3,221 |
| landslide | extra_trees | 0.0000 | 0.0000 | 0.0000 | 0.0349 | 0.8549 | 0.0021 | 0.0128 | 0.6 | 1,677,773 |
| landslide | hist_gradient_boosting | 0.0500 | 0.0312 | 0.0385 | 0.0185 | 0.7859 | 0.0026 | 0.0064 | 6.6 | 135,324 |
| landslide | logistic_regression | 0.0171 | 0.6250 | 0.0332 | 0.0249 | 0.8030 | 0.1586 | 0.1205 | 0.3 | 3,565 |
| landslide | random_forest | 0.0000 | 0.0000 | 0.0000 | 0.0203 | 0.8328 | 0.0039 | 0.0096 | 1.3 | 601,789 |
| windstorm | decision_tree | 0.0520 | 0.4423 | 0.0931 | 0.0441 | 0.6482 | 0.1761 | 0.1289 | 0.3 | 5,098 |
| windstorm | extra_trees | 0.1515 | 0.0321 | 0.0529 | 0.0789 | 0.7996 | 0.0039 | 0.0395 | 0.8 | 2,537,125 |
| windstorm | hist_gradient_boosting | 0.1408 | 0.0641 | 0.0881 | 0.0771 | 0.7440 | 0.0085 | 0.0263 | 6.3 | 147,183 |
| windstorm | logistic_regression | 0.0524 | 0.5833 | 0.0961 | 0.0672 | 0.7679 | 0.2304 | 0.1644 | 0.4 | 3,567 |
| windstorm | random_forest | 1.0000 | 0.0064 | 0.0127 | 0.0777 | 0.7665 | 0.0000 | 0.0225 | 1.8 | 1,237,042 |

### Phase 7E tuning and validation selection

Two candidates per hazard were tuned with **20 deterministic randomized configurations each**: **12 candidates, 240 configurations, 3 expanding date-block CV folds** inside training, and **720 candidate-fold fits** when all configurations complete. All districts for a target date remain in the same fold. Selection and threshold search use validation only. Threshold grid: **0.10, 0.20, ..., 0.90**; maximum F1 is selected, with ties resolved by precision, recall, then lower false-alert rate. No probability calibrator was fitted.

| Hazard | Candidate A CV AP (SD) / validation AP | Candidate B CV AP (SD) / validation AP | Selected algorithm | Validation threshold | Selected validation F1 |
| --- | --- | --- | --- | ---: | ---: |
| coldwave | Extra Trees 0.0766 (0.0436) / 0.0824 | Random Forest 0.0788 (0.0471) / 0.0872 | Random Forest | 0.10 | 0.1553 |
| flood | Random Forest 0.1438 (0.0220) / 0.0522 | HistGradientBoosting 0.1420 (0.0560) / 0.0951 | HistGradientBoosting | 0.10 | 0.1905 |
| heatwave | Extra Trees 0.0808 (0.0434) / 0.4511 | HistGradientBoosting 0.0785 (0.0473) / 0.4571 | HistGradientBoosting | 0.10 | 0.4554 |
| heavy_rain | Logistic Regression 0.2428 (0.0243) / 0.1552 | Extra Trees 0.2532 (0.0255) / 0.1580 | Extra Trees | 0.10 | 0.2226 |
| landslide | Logistic Regression 0.0292 (0.0197) / 0.0279 | Extra Trees 0.0398 (0.0259) / 0.0387 | Extra Trees | 0.10 | 0.0000 |
| windstorm | Extra Trees 0.0257 (0.0119) / 0.0813 | Random Forest 0.0370 (0.0196) / 0.0907 | Random Forest | 0.40 | 0.1317 |

The feature-importance analysis used **3 permutation repeats** on validation rows only. Top contributors to reproducing the synthetic rule were: flood `rain_7d_end_of_day` (AP drop 0.06025); heavy rain `rain_3h_end_of_day` (0.04682); landslide `rain_12h_end_of_day` (0.00391); heatwave `temperature_2m_daily_max` (0.26907); coldwave `soil_temperature_28_100cm_mean_24h_daily_mean` (0.02487); windstorm `wind_gusts_10m_daily_max` (0.00956). These are neither causal findings nor real-hazard importance estimates.

### One-time chronological test evaluation

The final test interval was read **once**, on 2026-09-25 at 18:45:24 UTC. No model, threshold or feature selection was changed using test results. Each row below represents **20,700 synthetic district-days**; altogether that is 124,200 hazard-row evaluations, not 124,200 distinct days. Thresholds were selected on validation. `AP` is average precision.

| Hazard | Test positives | Threshold | AP | ROC-AUC | Precision | Recall | F1 | False-alert rate | Brier |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| flood | 92 | 0.10 | 0.0596 | 0.8329 | 0.0870 | 0.0435 | 0.0580 | 0.0020 | 0.0048 |
| heavy_rain | 624 | 0.10 | 0.2040 | 0.8679 | 0.1931 | 0.4391 | 0.2682 | 0.0570 | 0.0263 |
| landslide | 81 | 0.10 | 0.0198 | 0.8586 | 0.0000 | 0.0000 | 0.0000 | 0.0002 | 0.0039 |
| heatwave | 2,958 | 0.10 | 0.4036 | 0.7998 | 0.4736 | 0.2786 | 0.3508 | 0.0516 | 0.1222 |
| coldwave | 1,491 | 0.10 | 0.2176 | 0.7704 | 0.3087 | 0.1737 | 0.2223 | 0.0302 | 0.0652 |
| windstorm | 367 | 0.40 | 0.0472 | 0.6855 | 0.0494 | 0.2071 | 0.0797 | 0.0720 | 0.0575 |

Persisted subgroup artifact has **150 rows**: 6 overall, 120 district rows (20 per hazard) and 24 season rows (4 per hazard). Metrics are suppressed where a subgroup has fewer than **5 positive or 5 negative cases**; subgroup support remains in the CSV. The landslide model produced **zero test true positives** at its validation-selected threshold and F1 **0.0000**. Flood AP is **0.0596**, heavy-rain AP **0.2040**, and windstorm AP **0.0472**. These figures only score recovery of the synthetic rule labels, not prediction of actual disasters.

## API, Live Weather and User Interface

- **API:** FastAPI with routes `GET /api/health`, `GET /api/districts`, `GET /api/registry`, `POST /api/predictions`, `POST /api/allocations`, `GET /api/alerts` and `GET /api/runs`.
- **Model registry:** loads six `phase7e_v1` development models, checks model SHA-256, scope/version, the 68-feature contract and sealed test-evaluation metadata. Scores are uncalibrated estimator outputs, not calibrated probabilities.
- **Historical replay:** label-free snapshot for 20 districts x 68 predictors = **1,360 feature values**, with feature reference date **2025-10-30** and target date **2025-10-31**. It fingerprints `data/processed/weather_features.csv`; the validator reports the source hash unchanged.
- **Live provider:** Open-Meteo ECMWF hourly endpoint, no API key, `Asia/Kolkata` application timezone. The adapter requests 15 hourly weather fields across the recent past and forecast, then requires a complete 24-hour prior local day and exactly 68 finite engineered values. Target-day weather is excluded. Missing fields, nulls, irregular hourly timestamps or an incomplete day make the district unavailable; no zero imputation is done. API timeout defaults to **20 seconds**.
- **Recorded live smoke check:** one real district, Srinagar; feature reference **2026-09-25**, target **2026-09-26**, 68 finite features and six scores. The recorded sample weather summary was mean temperature **17.779 C**, precipitation **0.0 mm**, mean wind **2.0458 km/h**, weather code **2.0**. This was a single-district smoke check, not a 20-district operational availability test.
- **React UI:** React 19, TypeScript 5.7, Vite 6.4, Leaflet 1.9 / React-Leaflet 5. It provides replay/live mode, a 20-point reference map, district detail, six score rows, signal history and allocation simulation. Map markers are weather source lookup coordinates, not district centroids or boundaries; the available boundary set did not exactly cover all 20 districts, so no boundary polygons are inferred.
- **Signals:** threshold exceedances are stored with `DEVELOPMENT_SIGNAL_NOT_FOR_DISPATCH`; outbound SMS/email is disabled.
- **Persistence:** local SQLite stores development prediction runs, signals and allocation runs. Default file: `data/runtime/jk_disaster_demo.sqlite3`.
- **Demo allocation:** inventory is `SIMULATED_DEVELOPMENT_ONLY`: **4 response-team slots, 50 medical-kit slots, 60 water-crate slots**. At most one team slot is assigned to a signaled district, and kit/water assignments are capped by remaining demo inventory. Priority is maximum uncalibrated development score + **5 points** per additional synthetic threshold signal, capped at **100**. There are no population, exposure or actual supply inputs; allocation status is `SIMULATION_ONLY_NOT_FOR_DISPATCH`.
- **Supabase:** optional REST mirror and SQL migration exist. Tables cover prediction runs, development alerts and allocation runs; RLS is enabled with no anonymous/public policies. The service-role secret stays server-side. No project credentials were provided, so Supabase is not connected; SQLite remains active.
- **Containers/CI:** API and frontend Dockerfiles, Compose and a GitHub Actions workflow are present. Compose defaults the web binding to `127.0.0.1:8080`; API is internal on 8000. The workflow specifies Python 3.12 and Node 22, API tests, frontend build and both Docker image builds. Docker was unavailable in the local implementation environment, so container builds and deployment are unverified.

## Testing and Validation Record

### Saved or previously observed passes

| Check | Recorded result | Scope |
| --- | --- | --- |
| `results/weather_validation_report.csv` | PASS for 20 districts + summary; 0 duplicate rows/timestamps and 0 missing cells in raw hourly files. | Historical source integrity and coverage. |
| Phase 4 assessment artifact | Assessment documents the 32 flood positives, five other zero-label tracks and source/hash safeguards. | Label evidence audit; not a negative-label validation. |
| Phase 7B synthetic-label validation | PASS; 42,620 rows, 20 districts, metadata, label states, threshold-period and raw/processed fingerprint checks. | Synthetic label artifact only. |
| Phase 7C model-ready validation | PASS for six targets; alignment, leakage, metadata, chronological split and district coverage checks. | Synthetic development datasets only. |
| Phase 7D baseline validation | PASS; 30 models reproduced, 0 recorded failures; test split not read. | Train/validation only. |
| Phase 7E selection validation | PASS; 12 candidates / 6 selections; frozen dataset hashes and validation thresholds reproduce. Validator does not reopen test rows. | Train/validation and artifact metadata. |
| Phase 7E final-test artifact validation | PASS; 6 overall + 144 subgroup metrics; threshold seals retained. Validator reads saved metrics/metadata, not dataset/model rows. | Persisted one-time test result. |
| Phase 8 replay snapshot validation | PASS; 20 districts x 68 features; one-day alignment; no labels; weather-source fingerprint unchanged. | Label-free replay artifact. |
| `python -m unittest tests.test_phase8_api -v` | Previously recorded: **4 tests passed**. | Health/replay contract, bounded allocation, target-day invariance under changed future weather, fail-closed missing inputs. |
| `npm run build` | Previously recorded successful Vite build: TypeScript check plus 1,626 modules; JS 399.97 kB (gzip 121.19 kB), CSS 27.68 kB (gzip 9.63 kB), HTML 0.46 kB (gzip 0.30 kB). | React/Vite production bundle. |
| Browser QA | Previously recorded: replay and simulated allocation exercised; 20/20 districts, desktop and 375 px mobile, no horizontal overflow or browser console errors. | Local development UI. |
| Python AST check / `git diff --check` | Previously recorded: 13 Python files passed AST syntax; diff whitespace check exit 0 (line-ending warnings only). | Source syntax / diff hygiene. |

### Recheck limitations while preparing this report

- In this report session, `python -m unittest tests.test_phase8_api -v` could not start because neither `python`, `py` nor `python3` is available on the shell PATH. The four-pass result above is from the earlier implementation validation record, not a fresh rerun here.
- A fresh `npm run build` attempt failed before Vite could bundle its config: Windows returned `EPERM` opening a timestamped file under `frontend/node_modules/.vite-temp/`. The previous successful build record remains, but this report-session rerun did not pass.
- Docker availability was not present in the recorded local implementation environment. No Docker image or hosted deployment is claimed.
- The sealed one-time final test evaluator was deliberately **not** rerun. Its evaluator refuses a second test-row read; only its persisted report/metrics and metadata seal were reviewed.

## Risks and Remaining Blockers

1. **Verified labels:** no verified negative flood district-days; sparse positives and incomplete/one-source event ascertainment. Other five hazards have no accepted project-period verified event labels.
2. **Independent evidence and evaluation:** collect audited event/non-event evidence over enough districts, years and independent events to support every chronological split. Avoid counting neighboring district-days from one storm as independent episodes. Freeze source completeness rules before inspecting predictors.
3. **Operational skill:** synthetic metrics cannot establish real-world recall, false-alarm burden, calibration, spatial transfer or benefit. Rebuild and evaluate only after real verified labels meet a documented sample/power and coverage plan.
4. **Live input coverage:** only one real district was live-smoke-tested. The all-district workflow can be partial/unavailable when provider fields or complete prior-day observations are missing.
5. **Exposure and response logic:** there is no verified population/exposure/vulnerability layer, official resource ledger, response protocol or real allocation optimization.
6. **Security and deployment:** no user authentication or production security review; do not expose the current local-development stack publicly. Supabase is unconfigured, Docker builds are unverified, and no deployed environment is recorded.
7. **Geography:** weather reference points do not substitute for district boundaries. The current map is point-based.
8. **Reproducibility:** the report references saved summaries and metrics under `results/`, synthetic datasets under `data/development/`, and model files under `models/development/`. Dataset hashes are recorded in their validation/model metadata. The test split remains sealed.

## Key Artifact Index

- Historical weather / feature quality: `results/weather_validation_report.csv`, `results/merged_weather_summary.csv`, `results/weather_feature_summary.csv`.
- Disaster evidence assessment: `results/phase4_disaster_data_assessment.md`, `results/phase4_disaster_data_assessment.csv`, `results/daily_flood_dataset_summary.csv`.
- Dataset contract and splits: `results/phase5_ml_dataset_design.md`, `results/phase5_ml_dataset_summary.csv`, `results/phase5_temporal_split_plan.csv`.
- Negative-label strategy/source audit: `results/phase6_label_strategy.md`, `results/phase6_source_coverage_matrix.csv`.
- Synthetic rule definitions and validation: `results/phase7_synthetic_label_design.md`, `results/phase7b_synthetic_label_validation.md`, `results/phase7c_model_ready_dataset_validation.md`.
- Baseline/tuning/test metrics: `results/ml/phase7d_baseline_report.md`, `results/ml/phase7e_model_selection.md`, `results/ml/phase7e_final_test_evaluation.md`, `results/ml/phase7e_validation_importance.md`; detailed test subgroup CSV `results/ml/phase7e/final_test_metrics.csv`.
- Application, setup and safety notes: `README.md`, `api/`, `frontend/`, `db/migrations/001_phase9_development_schema.sql`, `docker-compose.yml`, `.github/workflows/ci.yml`.

**Bottom line:** The weather-data and development-software path is substantially implemented and has useful leakage/contract tests. The project is **not ready for real supervised disaster prediction or emergency operations** until independently verified negative/event evidence, adequate temporal/spatial sample support, operational data, security controls and deployment validation are in place.
