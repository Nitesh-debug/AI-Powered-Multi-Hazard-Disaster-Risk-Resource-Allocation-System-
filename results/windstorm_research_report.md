# Phase 4E Windstorm Historical Data Research

## Scope

Research target: reliable windstorm-related event records for the 20 Jammu & Kashmir project districts from `2020-01-01` through `2025-10-31`.

No windstorm labels were created from wind speed or gust observations. Cyclones, thunderstorm warnings, rainstorms, squalls, gales, severe winds, and generic wind observations were kept as distinct source concepts.

## Sources investigated

| Source | Classification | Event type / result |
| --- | --- | --- |
| IMD Cyclone Information | D. NOT SUITABLE FOR GENERIC WINDSTORM LABELS IN THIS RUN | Cyclone outlooks, tracks, wind warnings, storm-surge warnings, and preliminary cyclone reports. No verified J&K generic windstorm event table obtained. |
| IMD Climate Services | B. PARTIALLY SUFFICIENT | Public climate maps, realized weather, warnings, and historical-data route. No machine-readable dated J&K windstorm event records exposed. |
| IMD Data Service Portal | B. PARTIALLY SUFFICIENT | Historical station observations and station metadata are advertised; wind speed, gust, and direction may be available by product. Access was not obtained. Observations are inputs, not labels. |
| NOAA Integrated Surface Database | B. PARTIALLY SUFFICIENT | Global hourly station observations include wind speed, direction, gust, and daily maximum gust. Station metadata identified 15 Indian stations in the J&K bounding area. No event classification is supplied. |
| NOAA ISD station history | B. PARTIALLY SUFFICIENT | Downloaded station metadata identifies station IDs, names, coordinates, and availability ranges. It contains no wind observations or event labels. |
| NOAA IBTrACS | D. NOT SUITABLE FOR GENERIC WINDSTORM LABELS | Global tropical cyclone best-track data with intensity and track information. Cyclone is not automatically mapped to the project's generic windstorm class. |
| Copernicus ERA5-Land | D. NOT SUITABLE FOR LABELS | Hourly gridded reanalysis with wind variables; provides modeled inputs, not documented windstorm events. |
| NDMA Cyclone guidance | C. SUPPORTING ONLY | Official cyclone definitions and intensity classes, not a dated J&K windstorm inventory. |

## Sources successfully obtained

- `data/raw/disasters/windstorm_sources/NOAA_ISD_station_history.csv`: official NOAA station-history CSV.
- `data/raw/disasters/windstorm_sources/NOAA_ISD_JK_bbox_india_stations.csv`: 15 Indian stations in the J&K bounding area.
- `data/raw/disasters/windstorm_inventory.csv`: empty evidence-only event inventory with documented schema.

The 15 Indian NOAA stations include Srinagar, Gulmarg, Sonamarg, Qazi Gund, Banihal, Jammu, Kathua, Dras, and related stations. Station availability ranges differ; several extend through 2024–2025. No district was assigned from coordinates because a deterministic district-boundary mapping was not performed.

## Event-type distinction

- **Cyclone:** covered by IMD cyclone products and NOAA IBTrACS; not treated as generic windstorm.
- **Severe wind / damaging wind:** no verified J&K event rows obtained.
- **Squall / gale:** no verified J&K event rows obtained.
- **Thunderstorm-related damaging wind:** no verified J&K event rows obtained.
- **Tornado / dust storm:** no verified J&K event rows obtained.
- **Wind observation:** available through NOAA ISD metadata/data products and IMD station services, but an observation is not an event label.

## Coverage findings

- Candidate dated windstorm event records: **0**.
- J&K event records: **0**.
- Project-district event records: **0**.
- Event date range: unavailable.
- Event classifications: unavailable.
- Event severity/impacts: unavailable.
- Event duration: unavailable.
- Station metadata records in J&K bounding area, India: **15**.
- Wind speed/gust/direction observation availability: advertised by NOAA ISD; values were not downloaded in this pass.

## Label suitability and next step

The NOAA ISD and IMD data services make a later observation-based curation phase possible. That phase would need to obtain station observations, establish deterministic station-to-district mapping using a documented boundary source, define an official severe-wind criterion or use independently documented event reports, and preserve station IDs and event types. It must not turn every high-wind observation into a windstorm label.

IBTrACS can support cyclone-specific research, but cyclone records should remain a separate class unless the project taxonomy is explicitly changed.

## Validation

- Candidate event records: 0.
- J&K event records: 0.
- Project-district event records: 0.
- Missing dates in inventory: 0.
- Duplicate event IDs: 0.
- Duplicate event-date-station combinations: 0.
- Missing district/station/wind/gust/event-type values in inventory: 0 because the inventory is empty.
- Synthetic records: none.
- Weather-derived labels: none.
- Flood files modified: no.
- Landslide files modified: no.
- Heatwave files modified: no.
- Coldwave files modified: no.
- Weather files modified: no.
- ML models trained: no.

Validation command: `python scripts/validate_windstorm_research.py`.

## Major limitations

No public, machine-readable, dated J&K windstorm event inventory was obtained. NOAA provides relevant station observations, but not event labels; IMD provides historical data access routes, but station data and official event declarations were not obtained. The 15 bounding-area stations cannot be silently treated as coverage for all 20 project districts.

## Final decision

**PARTIALLY SUFFICIENT — NEED CURATION / OFFICIAL CRITERIA APPLICATION**
