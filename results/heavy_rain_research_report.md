# Phase 4F Heavy Rain Historical Data Research

## Scope

Research target: documented heavy-rainfall events for the 20 Jammu & Kashmir project districts from `2020-01-01` through `2025-10-31`.

No heavy-rain labels were created from Open-Meteo precipitation or engineered rainfall features. Floods, cloudbursts, thunderstorms, and high rainfall observations were not automatically converted into heavy-rain events.

## Sources investigated

| Source | Classification | Result |
| --- | --- | --- |
| IMD Rainfall Information | B. PARTIALLY SUFFICIENT | Public service exposes all-India district, state-wise, station rainfall, rainfall statistics, monitoring maps, and station rainfall products. No downloadable J&K 2020–2025 event table was obtained. |
| IMD Data Service Portal | B. PARTIALLY SUFFICIENT | Historical station observations, station lists, climate tables, historical extremes, and data access are advertised. No authenticated historical station dataset was obtained. |
| NOAA Integrated Surface Database | B. PARTIALLY SUFFICIENT | Machine-readable station observations include precipitation amounts and time fields. No official heavy-rain classification or J&K event inventory is supplied. |
| NOAA Global Summary of the Day | B. PARTIALLY SUFFICIENT | Daily station summaries include precipitation amount. Observations can support later 24-hour criteria work, but are not labels. |
| NASA GPM IMERG | D. NOT SUITABLE FOR LABELS | Public global precipitation estimates from 1998 onward; no official event classification or station observations. |
| Copernicus ERA5-Land | D. NOT SUITABLE FOR LABELS | Hourly global gridded reanalysis from 1950 onward; provides modeled precipitation inputs, not documented events. |
| NDMA Flood guidance | C. SUPPORTING ONLY | Discusses floods and rainfall hazards, not a heavy-rain event inventory. |

## Official rainfall-intensity terminology

IMD operational rainfall terminology is based on 24-hour rainfall measured at a station, commonly reported for the 24-hour period ending at 0830 IST:

- **Heavy rain:** 64.5–115.5 mm.
- **Very heavy rain:** 115.6–204.4 mm.
- **Extremely heavy rain:** 204.5 mm or more.

These thresholds are official intensity categories, not automatically documented disaster events. A later criteria-application phase would need the appropriate daily station observation, the observation window/time zone, station identity, and deterministic station-to-district mapping. The accessible public IMD page exposed rainfall products and station interfaces but not a machine-readable historical J&K event table.

Cloudburst, thunderstorm, flood, and flash flood remain separate event types. A cloudburst or flood record is not copied into this heavy-rain inventory unless the source explicitly classifies the rainfall event in the required terminology.

## Candidate records and coverage

- Candidate heavy-rain event records found: **0**.
- J&K event records: **0**.
- Project-district event records: **0**.
- Earliest/latest candidate date: unavailable.
- Station rainfall records obtained: **0**.
- Official classifications obtained: **0**.
- Rainfall amount/window records accepted: **0**.
- Cloudburst-specific records accepted: **0**.
- Severity/impact records: **0**.
- Duration records: **0**.

The `heavy_rain_inventory.csv` file is intentionally empty and contains only the documented schema for future verified records.

## Applicability to later curation

IMD and NOAA provide observation pathways that could support a later official-criteria application phase. That phase must obtain daily station rainfall totals with the correct 24-hour window, preserve station IDs and original locations, and document station-to-district mapping. It must not use Open-Meteo values as historical ground-truth labels or treat high rainfall as a documented event.

NASA GPM and ERA5-Land may support precipitation context or input features, but neither supplies official J&K heavy-rain event labels.

## Validation

- Candidate event records: 0.
- J&K records: 0.
- Project-district records: 0.
- Missing dates in inventory: 0.
- Duplicate event IDs: 0.
- Duplicate event-date-station combinations: 0.
- Missing district/station/rainfall/window/classification values in inventory: 0 because the inventory is empty.
- Synthetic records: none.
- Weather-derived labels: none.
- Flood files modified: no.
- Landslide files modified: no.
- Heatwave files modified: no.
- Coldwave files modified: no.
- Windstorm files modified: no.
- Weather files modified: no.
- ML models trained: no.

Validation command: `python scripts/validate_heavy_rain_research.py`.

## Recommended next step

Obtain authorized IMD station rainfall data or a verified historical district rainfall export for 2020–2025. Apply the official 24-hour rainfall categories only after validating station coverage, observation windows, and district mapping. Keep heavy rain separate from flood, cloudburst, thunderstorm, and flash-flood labels.

## Major limitations

No public machine-readable dated J&K heavy-rain event inventory was obtained. Observation products exist, but they require access and curation before they can support labels. Absence of a record does not mean the date was free of heavy rain.

## Final decision

**PARTIALLY SUFFICIENT — NEED CURATION / OFFICIAL CRITERIA APPLICATION**
