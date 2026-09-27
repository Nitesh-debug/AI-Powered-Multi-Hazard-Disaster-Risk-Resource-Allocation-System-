# Phase 7A Synthetic Development-Label Design

## Status and scope

**ALL LABELS IN THIS DOCUMENT ARE SYNTHETIC/DEVELOPMENT ONLY.**

This document defines a development schema. It does not create label rows, alter raw or processed data, describe observed historical disasters, integrate an API, provide operational warnings, or train a model.

Synthetic labels may later be used only to test data plumbing, multi-label handling, temporal splitting, metrics code, API contracts, and user-interface states. They must never be joined to or presented as verified historical disaster labels.

## Dataset contract

- Unit: one `district` and one `target_date`.
- Coverage available for later development: 20 districts from `2020-01-01` through `2025-10-31` in `weather_features.csv`.
- Source grain: hourly. Each rule below uses the final valid hourly rolling value on `target_date`, unless the rule explicitly uses a daily maximum/minimum or a prior date.
- Multi-label behavior: the six labels are independent and may trigger together.
- Value contract: `1` means `SYNTHETIC_TRIGGER`, `0` means `SYNTHETIC_NO_TRIGGER`, and missing means `UNAVAILABLE` because a required input or threshold is missing.
- Required constant metadata: `synthetic_label_scope = SYNTHETIC_DEVELOPMENT_ONLY` and `synthetic_rule_version = phase7a_v1`.
- A missing input must produce `UNAVAILABLE`, never `0`.
- Existing verified flood labels and `NO_VERIFIED_EVENT` statuses remain separate and unchanged.

## Threshold calibration

The rules use relative thresholds because the available file contains district-point weather features, not verified station-based disaster declarations. This avoids claiming that an unverified absolute weather cutoff is an official disaster definition.

1. Build one daily endpoint record per district from the existing hourly features without modifying `weather_features.csv`.
2. Estimate thresholds only from the Phase 5 training target period, `2020-01-02` through `2021-12-31`.
3. Freeze all thresholds before applying rules to validation or test dates. Never recalculate thresholds from validation or test data.
4. Use district and meteorological season thresholds for rain, soil moisture, and wind. Seasons are DJF, MAM, JJA, and SON.
5. Use district and calendar-month thresholds for temperature.
6. For rain percentiles, use valid days with positive rain only. This prevents a zero percentile in dry periods from making every dry day a trigger.
7. Require at least 30 valid daily observations for a district-period threshold. If unavailable, fall back from district-month to district-season where applicable, then to the district's full training period. If the district threshold is still unavailable, return `UNAVAILABLE`; do not borrow another district's threshold.

Notation used below:

- `Qp(x)` is the frozen training-period percentile `p` for the stated district and period stratum.
- `EOD(x, t)` is the final valid value of rolling feature `x` on target date `t`.
- `PREV(condition, t)` means the same condition was true for that district on calendar date `t - 1`.

## Hazard schemas

### Flood

- **Synthetic label name:** `synthetic_flood_dev_v1`
- **Classification:** **SYNTHETIC/DEVELOPMENT ONLY**
- **Input weather features:** `rain_24h`, `rain_7d`, `soil_moisture_28_100cm_mean_24h`, plus `district` and `time` for grouping.
- **Transparent rule:** Set to `1` when all of the following hold on target date `t`:
  - `EOD(rain_24h, t) > 0`
  - `EOD(rain_24h, t) >= Q95(rain_24h)`
  - `EOD(rain_7d, t) >= Q90(rain_7d)`
  - `EOD(soil_moisture_28_100cm_mean_24h, t) >= Q90(soil_moisture_28_100cm_mean_24h)`
  - Set to `0` only when every required value and threshold is available and at least one condition is false. Otherwise set to `UNAVAILABLE`.
- **Label meaning:** A locally unusual combination of intense recent rain, sustained weekly wetness, and high deeper-layer soil moisture. It is a synthetic flood-like weather scenario, not evidence of inundation.
- **Limitations:** The rule has no river level, catchment flow, drainage capacity, snowmelt attribution, reservoir release, floodplain, terrain, infrastructure, exposure, impact, or official incident evidence. Flooding can occur without this pattern, and this pattern can occur without flooding.

### Heavy rain

- **Synthetic label name:** `synthetic_heavy_rain_dev_v1`
- **Classification:** **SYNTHETIC/DEVELOPMENT ONLY**
- **Input weather features:** `rain_24h`, plus `district` and `time` for grouping.
- **Transparent rule:** Set to `1` when `EOD(rain_24h, t) > 0` and `EOD(rain_24h, t) >= Q95(rain_24h)` for the district and season. Set to `0` only when the value and threshold are available and the condition is false. Otherwise set to `UNAVAILABLE`.
- **Label meaning:** A trailing 24-hour rain amount in the upper 5 percent of positive-rain training days for that district and season.
- **Limitations:** This is a relative development threshold, not an IMD heavy-rain declaration. The data are district-point weather inputs rather than validated station observations, and the source timestamp day may not match an official observation window. It does not imply flooding or damage.

### Landslide

- **Synthetic label name:** `synthetic_landslide_dev_v1`
- **Classification:** **SYNTHETIC/DEVELOPMENT ONLY**
- **Input weather features:** `rain_3d`, `soil_moisture_0_7cm_mean_24h`, `soil_moisture_0_7cm_change_24h`, plus `district` and `time` for grouping.
- **Transparent rule:** Set to `1` when all of the following hold on target date `t`:
  - `EOD(rain_3d, t) >= Q95(rain_3d)`
  - `EOD(soil_moisture_0_7cm_mean_24h, t) >= Q90(soil_moisture_0_7cm_mean_24h)`
  - `EOD(soil_moisture_0_7cm_change_24h, t) > 0`
  - `EOD(soil_moisture_0_7cm_change_24h, t) >= Q90(soil_moisture_0_7cm_change_24h)`
  - Set to `0` only when every required value and threshold is available and at least one condition is false. Otherwise set to `UNAVAILABLE`.
- **Label meaning:** A synthetic rainfall-induced slope-instability weather scenario with unusually high three-day rain, wet shallow soil, and a strong recent moisture increase.
- **Limitations:** No slope, geology, soil type, land cover, road cutting, seismic activity, drainage, antecedent failures, coordinates, impact reports, or verified landslide inventory is used. It cannot indicate that a landslide occurred.

### Heatwave

- **Synthetic label name:** `synthetic_heatwave_dev_v1`
- **Classification:** **SYNTHETIC/DEVELOPMENT ONLY**
- **Input weather features:** `temperature_max_24h`, plus its district-level prior-date value derived from daily endpoints; `district` and `time` provide grouping.
- **Transparent rule:** Define `hot(d, t)` as `EOD(temperature_max_24h, t) >= Q95(temperature_max_24h)` for the district and calendar month. Set the label to `1` when `hot(d, t)` and `PREV(hot, t)` are both true. Set it to `0` only when both dates and thresholds are available and the two-day condition is false. Otherwise set to `UNAVAILABLE`.
- **Label meaning:** The second or later day of a synthetic two-day spell of locally extreme daily maximum temperature.
- **Limitations:** This is not an IMD heatwave declaration. It lacks official station normals, absolute temperature criteria, departure from normal, terrain or plains classification, humidity stress, nighttime heat criteria, exposure, impacts, and official duration rules.

### Coldwave

- **Synthetic label name:** `synthetic_coldwave_dev_v1`
- **Classification:** **SYNTHETIC/DEVELOPMENT ONLY**
- **Input weather features:** `temperature_min_24h`, plus its district-level prior-date value derived from daily endpoints; `district` and `time` provide grouping.
- **Transparent rule:** Define `cold(d, t)` as `EOD(temperature_min_24h, t) <= Q05(temperature_min_24h)` for the district and calendar month. Set the label to `1` when `cold(d, t)` and `PREV(cold, t)` are both true. Set it to `0` only when both dates and thresholds are available and the two-day condition is false. Otherwise set to `UNAVAILABLE`.
- **Label meaning:** The second or later day of a synthetic two-day spell of locally extreme daily minimum temperature.
- **Limitations:** This is not an IMD coldwave declaration. It lacks official station normals, absolute and departure-from-normal criteria, terrain or regional classification, wind chill, snow-cover effects, exposure, impacts, and official duration rules.

### Windstorm

- **Synthetic label name:** `synthetic_windstorm_dev_v1`
- **Classification:** **SYNTHETIC/DEVELOPMENT ONLY**
- **Input weather features:** `wind_gust_max_24h`, `wind_speed_max_24h`, plus `district` and `time` for grouping.
- **Transparent rule:** Set to `1` when `EOD(wind_gust_max_24h, t) >= Q99(wind_gust_max_24h)` and `EOD(wind_speed_max_24h, t) >= Q95(wind_speed_max_24h)` for the district and season. Set to `0` only when both values and thresholds are available and the joint condition is false. Otherwise set to `UNAVAILABLE`.
- **Label meaning:** A synthetic locally extreme wind-and-gust scenario relative to the district's training-period weather.
- **Limitations:** This is not an official windstorm, squall, gale, thunderstorm, or cyclone label. It lacks verified station observations, event duration, direction changes, convective context, damage, exposure, official thresholds, and event taxonomy.

## Proposed development-label columns

| Column | Type | Allowed values | Purpose |
| --- | --- | --- | --- |
| `district` | string | Existing project district | Join key only. |
| `target_date` | date | Source-time calendar date | Daily target key. |
| `synthetic_label_scope` | string | `SYNTHETIC_DEVELOPMENT_ONLY` | Mandatory warning carried with every row. |
| `synthetic_rule_version` | string | `phase7a_v1` | Reproducibility and change control. |
| `synthetic_flood_dev_v1` | nullable integer | `1`, `0`, or missing | Synthetic flood-like trigger. |
| `synthetic_heavy_rain_dev_v1` | nullable integer | `1`, `0`, or missing | Synthetic heavy-rain trigger. |
| `synthetic_landslide_dev_v1` | nullable integer | `1`, `0`, or missing | Synthetic landslide-condition trigger. |
| `synthetic_heatwave_dev_v1` | nullable integer | `1`, `0`, or missing | Synthetic sustained-heat trigger. |
| `synthetic_coldwave_dev_v1` | nullable integer | `1`, `0`, or missing | Synthetic sustained-cold trigger. |
| `synthetic_windstorm_dev_v1` | nullable integer | `1`, `0`, or missing | Synthetic extreme-wind trigger. |
| `synthetic_unavailable_reason` | nullable string | Explicit missing input or threshold reason | Prevents missing evidence from becoming a synthetic zero. |

Threshold values and calibration counts should be stored in a separate versioned development artifact if implementation is later approved. They must not be written into raw or existing processed weather files.

## Leakage and use restrictions

- The rule is evaluated on weather for `target_date`. For any later one-day-ahead development model, predictors must end on `feature_reference_date = target_date - 1 day` as required by Phase 5.
- Target-date weather values used to generate a synthetic label must never appear in that row's predictor inputs.
- Thresholds, missing-value handling, and any later feature selection must be fitted on the training period only and frozen for later periods.
- Keep chronological train, validation, and test periods. Do not randomly split district-date rows.
- Synthetic labels must be stored separately from verified labels and must never overwrite `flood_event_label`, `label_status`, or provenance fields.
- Performance against these targets measures reproduction or prediction of the synthetic weather rules only. It does not measure disaster forecasting skill.
- No alert, resource allocation, public claim, historical event count, or operational risk score may be based on these labels.

## Phase 7A outcome

The six label definitions are suitable for later development-pipeline testing only. They are not suitable as real historical disaster labels, verified negatives, or evidence that any hazard occurred or did not occur.
