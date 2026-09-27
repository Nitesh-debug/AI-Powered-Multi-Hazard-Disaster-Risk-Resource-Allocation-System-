# Phase 7B Synthetic Development-Label Validation

## Result

**PASS**

This artifact contains synthetic development targets only. It does not contain verified historical disaster labels and no ML model was trained.

## Artifact

- Dataset: `data/development/phase7_synthetic_development_labels.csv`
- Rows: 42,620
- Districts: 20
- Target dates: `2020-01-01` to `2025-10-31`
- Scope: `SYNTHETIC_DEVELOPMENT_ONLY` on every row
- Rule version: `phase7a_v1` on every row
- SHA-256: `c5efba704023f08753fa6dc5e9024b21f310852dfd153ae553b5d3301e941998`

## Label counts

| Synthetic development label | Positive (`1`) | Zero (`0`) | `UNAVAILABLE` |
| --- | ---: | ---: | ---: |
| `synthetic_flood_dev_v1` | 166 | 42,334 | 120 |
| `synthetic_heavy_rain_dev_v1` | 1,132 | 41,488 | 0 |
| `synthetic_landslide_dev_v1` | 177 | 42,403 | 40 |
| `synthetic_heatwave_dev_v1` | 4,019 | 38,581 | 20 |
| `synthetic_coldwave_dev_v1` | 1,962 | 40,638 | 20 |
| `synthetic_windstorm_dev_v1` | 644 | 41,976 | 0 |

## Safeguards

- Processed weather, verified flood labels, and curated flood-event hashes are unchanged.
- Threshold calibration is restricted to `2020-01-02` through `2021-12-31`.
- The output contains no target-date weather feature columns.
- `feature_reference_date` is exactly one day before `target_date` on every row.
- Later one-day-ahead model-ready data must join predictors using `district` and `feature_reference_date`, never target-date weather.
- Missing rule inputs remain `UNAVAILABLE`; they are not converted to zero.
- Synthetic labels remain separate from verified disaster labels.
- ML models trained: No.
