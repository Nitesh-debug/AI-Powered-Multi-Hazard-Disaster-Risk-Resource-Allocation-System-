# Phase 4D Coldwave Historical Data Research

## Scope

Research target: reliable coldwave-event records for the 20 Jammu & Kashmir project districts during `2020-01-01` through `2025-10-31`.

No coldwave labels were created from the project's weather data. Low temperatures, frost, snowfall, freezing conditions, and anomalies were not converted into coldwave events. Flood, landslide, heatwave, and weather files were not modified.

## Sources investigated

| Source | Classification | Result |
| --- | --- | --- |
| IMD Cold Wave FAQ and criteria | B. USABLE AFTER CURATION / OFFICIAL CRITERIA APPLICATION | IMD exposes a Cold Wave FAQ section, but the accessible page did not provide machine-readable historical event rows or downloadable station normals. |
| NDMA Winter Cold Wave advisory | C. SUPPORTING ONLY | Official winter cold-wave safety guidance; no event records or quantitative station data. |
| IMD Data Service Portal | B. USABLE AFTER CURATION / OFFICIAL CRITERIA APPLICATION | Portal advertises station lists, climate tables, normals, historical extremes, free data access, and gridded climatology. No authenticated station observations or normals were obtained in this run. |
| IMD Climate Services | D. NOT SUITABLE FOR LABELS IN THIS RUN | Climate maps and public services are available, but no verified machine-readable J&K coldwave event table was exposed. |
| Copernicus ERA5-Land | D. NOT SUITABLE FOR LABELS | Hourly gridded reanalysis is an estimate, not a documented coldwave-event label or official station-normal source. |
| WMO public resources | D. NOT SUITABLE FOR LABELS IN THIS RUN | No J&K project-period coldwave event table was obtained. |

## Official coldwave criteria investigated

The standard IMD coldwave definition used operationally in India is station-based and relies on minimum temperature and departure from the station's normal minimum temperature. The commonly stated plains criterion is:

- minimum temperature of 10 C or less, together with a departure from normal minimum temperature of 4.5 C to 6.4 C for a cold wave;
- departure of 6.5 C or more for a severe cold wave;
- an actual minimum temperature of 4 C or less is also used for cold-wave declaration irrespective of departure in the plains criterion.

The accessible IMD FAQ page did not expose these criteria as machine-readable text during inspection, and the NDMA winter advisory page is non-quantitative. Therefore these values are recorded as the standard criterion to verify against an authorized IMD document before any application.

The public sources did not establish a separate, directly applicable numeric criterion for every hilly or mountain district in this project. This matters because the project spans Jammu plains/foothills, Kashmir valleys, and mountainous districts. A uniform plains threshold must not be applied to all 20 districts. A valid application requires station identity, terrain/region classification, daily minimum temperature, station normal minimum temperature, and a documented operational duration rule. No duration metadata was obtained.

## Candidate records and coverage

- Candidate coldwave event records found: **0**.
- Jammu & Kashmir records: **0**.
- Project-district records: **0**.
- Earliest candidate event date: unavailable.
- Latest candidate event date: unavailable.
- Station identifiers obtained: **0**.
- Minimum-temperature event values obtained: **0**.
- Normal minimum-temperature values obtained: **0**.
- Departure-from-normal values obtained: **0**.
- Explicit coldwave or severe-coldwave classifications: **0**.
- Severity values: **0**.
- Duration values: **0**.

The `coldwave_inventory.csv` file is intentionally empty and contains only the documented schema for future verified records.

## Applicability to current project weather

The project's Open-Meteo data contains district coordinate observations, not identified IMD stations, official IMD station normals, or official coldwave declarations. Applying the standard criterion to these points would be an unverified derived-label experiment and was not performed.

ERA5-Land may support climate context, but its reanalysis estimates are not documented coldwave events and cannot establish official labels by themselves.

## Validation

- Candidate records: 0.
- J&K records: 0.
- Project-district records: 0.
- Missing dates: 0.
- Duplicate event IDs: 0.
- Duplicate event-date-station combinations: 0.
- Missing district/station/minimum-temperature/normal/departure values in inventory: 0 because the inventory is empty.
- Synthetic records: none.
- Weather-derived labels: none.
- Flood files modified: no.
- Landslide files modified: no.
- Heatwave files modified: no.
- Weather files modified: no.
- ML models trained: no.

Validation command: `python scripts/validate_coldwave_research.py`.

## Recommended next step

Request or obtain authorized IMD historical station data and climate normals for J&K stations covering 2020–2025, including station IDs, daily minimum temperatures, normal minimum temperatures, terrain/region classification, official coldwave declarations, and duration metadata. Then verify deterministic station-to-district mapping before applying the official criterion.

## Major limitations

Publicly accessible sources inspected provide advisories, FAQ interfaces, climate services, or reanalysis rather than a machine-readable historical J&K coldwave event inventory. The project weather points cannot be treated as IMD station observations or normals. Absence of records does not mean absence of coldwaves.

## Final decision

**INSUFFICIENT — NO VERIFIED PROJECT-PERIOD COLDWAVE LABEL DATA FOUND**
