# Phase 4C Heatwave Historical Data Research

## Scope

Research target: reliable heatwave-event records for the 20 Jammu & Kashmir project districts from `2020-01-01` through `2025-10-31`.

No heatwave labels were created from the project's weather data. No hot-day, temperature-anomaly, or threshold-derived event was written. Flood, landslide, and weather files were not modified.

## Sources investigated

| Source | Classification | Result |
| --- | --- | --- |
| IMD Heat Wave FAQ and criteria | B. USABLE AFTER CURATION / OFFICIAL CRITERIA APPLICATION | Official criteria were found, but no historical J&K event table or station-normal download was publicly obtained. |
| NDMA Heat Wave guidance | B. USABLE AFTER CURATION / OFFICIAL CRITERIA APPLICATION | NDMA reproduces IMD criteria: minimum maximum temperature 40 C for plains and 30 C for hilly regions; departure thresholds depend on normal maximum temperature; 45 C or more triggers heatwave regardless of normal. No event records are provided. |
| IMD Climate Services | D. NOT SUITABLE FOR LABELS IN THIS RUN | Public page exposes daily temperature maps, realized weather, warnings, and climate products, but no downloadable historical J&K event table. |
| IMD Data Service Portal | B. USABLE AFTER CURATION / OFFICIAL CRITERIA APPLICATION | Historical station data service is available, but authentication/access and station normals were not obtained in this run. |
| IMD API documentation | D. NOT SUITABLE FOR LABELS IN THIS RUN | API documentation covers interfaces and alerts, not a historical event inventory. |
| Copernicus ERA5-Land | D. NOT SUITABLE FOR LABELS | Global hourly gridded reanalysis from 1950 to present under CC BY. It is an estimate/reanalysis, not an official event label or station-normal source. |
| NDMA heatwave guidance/advisories | C. SUPPORTING ONLY | Provides preparedness guidance, not dated event records. |

## Official heatwave criteria found

The accessible NDMA page attributes the following criteria to IMD:

- Heatwave is not considered until maximum temperature reaches at least 40 C for plains and at least 30 C for hilly regions.
- When normal maximum temperature is 40 C or less, heatwave departure is 5–6 C and severe heatwave departure is 7 C or more.
- When normal maximum temperature is above 40 C, heatwave departure is 4–5 C and severe heatwave departure is 6 C or more.
- When actual maximum temperature is 45 C or more, heatwave should be declared irrespective of the normal maximum temperature.

The accessible criteria do not provide a project-ready duration rule. They also require a valid classification of station terrain/region and reliable normal maximum temperature for the relevant station. The 20 project districts span plains and mountainous/hilly terrain, so one uniform threshold must not be forced across all districts.

## Candidate records and coverage

- Candidate heatwave event records found: **0**.
- Jammu & Kashmir records: **0**.
- Project-district records: **0**.
- Earliest candidate event date: unavailable.
- Latest candidate event date: unavailable.
- Station identifiers obtained: **0**.
- Maximum-temperature event values obtained: **0**.
- Normal-temperature values obtained: **0**.
- Explicit heatwave classifications obtained: **0**.
- Severity values obtained: **0**.
- Duration values obtained: **0**.

The `heatwave_inventory.csv` file is intentionally empty and contains only the documented schema for future verified records.

## Applicability to current project weather

The project's Open-Meteo data contains district coordinate weather series, not identified IMD station identifiers, official station normals, or official IMD heatwave declarations. Applying IMD thresholds to those series would be an official-criterion-derived label experiment requiring additional station/normal and terrain validation; it was not performed.

ERA5-Land was considered as a scientific source, but it is a model-based gridded reanalysis. It may support climate context or sensitivity analysis, but it is not a documented heatwave-event label source and cannot by itself establish official J&K heatwave events.

## Validation

- Candidate records: 0.
- J&K records: 0.
- Project-district records: 0.
- Missing dates: 0.
- Duplicate event IDs: 0.
- Duplicate event-date-station combinations: 0.
- Missing district/station/temperature/normal-temperature values in inventory: 0 because the inventory is empty.
- Synthetic records: none.
- Weather-derived labels: none.
- Flood files modified: no.
- Landslide files modified: no.
- Weather files modified: no.
- ML models trained: no.

Validation command: `python scripts/validate_heatwave_research.py`.

## Recommended next step

Request or obtain from IMD an authorized historical station dataset for J&K covering 2020–2025, including station identifiers, daily maximum temperature, long-term normal maximum temperature, station elevation/terrain classification, and any official heatwave declarations or duration metadata. Then validate station-to-district mapping before applying the official criterion.

## Major limitations

The publicly accessible sources inspected provide criteria, guidance, maps, or reanalysis rather than a machine-readable historical J&K event inventory. The current project weather series cannot be treated as IMD station observations or normals. Absence of records does not mean absence of heatwaves.

## Final decision

**INSUFFICIENT — NO VERIFIED PROJECT-PERIOD HEATWAVE LABEL DATA FOUND**
