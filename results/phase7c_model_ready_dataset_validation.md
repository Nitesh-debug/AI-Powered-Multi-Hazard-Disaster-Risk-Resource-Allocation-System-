# Phase 7C Model-Ready Synthetic Dataset Validation

## Result

**PASS**

Six hazard-specific supervised-development datasets were created. They contain synthetic development targets only; no verified disaster labels were changed or combined with them, and no ML model was trained.

## Dataset summary

| Target | Rows | Positive | Negative | Source `UNAVAILABLE` | Total excluded | Districts | Target dates | Features | Train | Validation | Test |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| `synthetic_flood_dev_v1` | 42,480 | 166 | 42,314 | 120 | 140 | 20 | `2020-01-08` to `2025-10-31` | 68 | 14,480 | 7,300 | 20,700 |
| `synthetic_heavy_rain_dev_v1` | 42,480 | 1,131 | 41,349 | 0 | 140 | 20 | `2020-01-08` to `2025-10-31` | 68 | 14,480 | 7,300 | 20,700 |
| `synthetic_landslide_dev_v1` | 42,480 | 177 | 42,303 | 40 | 140 | 20 | `2020-01-08` to `2025-10-31` | 68 | 14,480 | 7,300 | 20,700 |
| `synthetic_heatwave_dev_v1` | 42,480 | 4,019 | 38,461 | 20 | 140 | 20 | `2020-01-08` to `2025-10-31` | 68 | 14,480 | 7,300 | 20,700 |
| `synthetic_coldwave_dev_v1` | 42,480 | 1,962 | 40,518 | 20 | 140 | 20 | `2020-01-08` to `2025-10-31` | 68 | 14,480 | 7,300 | 20,700 |
| `synthetic_windstorm_dev_v1` | 42,480 | 644 | 41,836 | 0 | 140 | 20 | `2020-01-08` to `2025-10-31` | 68 | 14,480 | 7,300 | 20,700 |

`Total excluded` is the source-label row count minus final model-ready rows. It includes out-of-split dates, `UNAVAILABLE` targets, and rows lacking a complete prior-day predictor vector; categories may overlap.

## Split class counts

| Target | Split | Rows | Positive | Negative |
| --- | --- | ---: | ---: | ---: |
| `synthetic_flood_dev_v1` | train | 14,480 | 47 | 14,433 |
| `synthetic_flood_dev_v1` | validation | 7,300 | 27 | 7,273 |
| `synthetic_flood_dev_v1` | test | 20,700 | 92 | 20,608 |
| `synthetic_heavy_rain_dev_v1` | train | 14,480 | 346 | 14,134 |
| `synthetic_heavy_rain_dev_v1` | validation | 7,300 | 161 | 7,139 |
| `synthetic_heavy_rain_dev_v1` | test | 20,700 | 624 | 20,076 |
| `synthetic_landslide_dev_v1` | train | 14,480 | 64 | 14,416 |
| `synthetic_landslide_dev_v1` | validation | 7,300 | 32 | 7,268 |
| `synthetic_landslide_dev_v1` | test | 20,700 | 81 | 20,619 |
| `synthetic_heatwave_dev_v1` | train | 14,480 | 349 | 14,131 |
| `synthetic_heatwave_dev_v1` | validation | 7,300 | 712 | 6,588 |
| `synthetic_heatwave_dev_v1` | test | 20,700 | 2,958 | 17,742 |
| `synthetic_coldwave_dev_v1` | train | 14,480 | 316 | 14,164 |
| `synthetic_coldwave_dev_v1` | validation | 7,300 | 155 | 7,145 |
| `synthetic_coldwave_dev_v1` | test | 20,700 | 1,491 | 19,209 |
| `synthetic_windstorm_dev_v1` | train | 14,480 | 121 | 14,359 |
| `synthetic_windstorm_dev_v1` | validation | 7,300 | 156 | 7,144 |
| `synthetic_windstorm_dev_v1` | test | 20,700 | 367 | 20,333 |

## Validation checks

- Predictor contract: 68 Phase 5 weather features in every dataset.
- One-day alignment: `feature_reference_date = target_date - 1 day` on every row.
- Leakage: predictor values were independently reconstructed from `feature_reference_date`; no target-date weather, verified-label field, provenance field, or other hazard target is present.
- Label usability: each target contains only integer `0` or `1`; all `UNAVAILABLE` rows are excluded without conversion.
- Metadata: every row preserves `SYNTHETIC_DEVELOPMENT_ONLY` and `phase7a_v1`.
- Splits: Phase 5 train, validation, and test boundaries are chronological and non-overlapping; district-days were not randomly split.
- Coverage: all 20 districts occur in every hazard and every split.
- Inputs: frozen weather, synthetic-label, feature-schema, and split-plan hashes are unchanged.
- ML models trained: No.

## Artifacts

- `data/development/model_ready/phase7c_synthetic_flood_dev_v1.csv.gz` SHA-256: `1f5a1863ecc9d5f90613fc3a5e2622711a60fd4db142662a870e0073dc53ef6e`
- `data/development/model_ready/phase7c_synthetic_heavy_rain_dev_v1.csv.gz` SHA-256: `ce1132ffc0c071abcfacf0892b2009ed86fc0a2e5bf13c5fa7b3d6bb5d251d05`
- `data/development/model_ready/phase7c_synthetic_landslide_dev_v1.csv.gz` SHA-256: `d8e1936cac26329019ceaaf943a76b0dc315764781209c1b39e2ce96890fc05e`
- `data/development/model_ready/phase7c_synthetic_heatwave_dev_v1.csv.gz` SHA-256: `6be7fd7c7f05ff9bc5583f17c9bb5c5143c7a8e15b3ccfc354eca43a51717537`
- `data/development/model_ready/phase7c_synthetic_coldwave_dev_v1.csv.gz` SHA-256: `194a57af996e577ec734246a7490f7b04a9da92229ccef95398a3472ce7282ec`
- `data/development/model_ready/phase7c_synthetic_windstorm_dev_v1.csv.gz` SHA-256: `4ad98dd577fa19d4a65de5e707d67ac0affce8236ca22677c084bfc0e0f56707`
