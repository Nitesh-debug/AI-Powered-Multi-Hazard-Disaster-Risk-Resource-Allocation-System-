# Phase 4B Landslide Historical Data Research

## Scope

Research target: verified, machine-readable landslide events for the 20 Jammu & Kashmir project districts during `2020-01-01` through `2025-10-31`.

No weather thresholds were used. No absence of a record was interpreted as evidence that no landslide occurred. No flood files, weather files, labels, or models were modified.

## Sources investigated

| Source | Classification | Result |
| --- | --- | --- |
| NASA Global Landslide Catalog Export | D. NOT SUITABLE FOR LABELS for this project period | Official downloadable CSV was inspected. It contains event dates, coordinates, locations, triggers, descriptions, source names/links, and partial impacts. The export contains 11,033 records, 1,265 India records, and 201 records in the J&K bounding box, but no records from 2020 onward. |
| NASA COOLR / Landslide Viewer | D. NOT SUITABLE FOR LABELS IN THIS RUN | NASA's current page links to a live Earthdata ArcGIS experience. The current viewer item was inaccessible through the public metadata endpoint, and no verifiable machine-readable J&K 2020-2025 export was obtained. |
| NASA Landslide Reporter Catalog | D. NOT SUITABLE FOR LABELS IN THIS RUN | NASA documents the reporting tool, but no downloadable project-period J&K event table was obtained. |
| NASA Rapid-Response Landslide Inventories | D. NOT SUITABLE FOR LABELS IN THIS RUN | NASA lists the inventory family, but no accessible project-period J&K export was obtained. |
| NASA High Mountain Asia Multitemporal Landslide Inventories | B. USABLE AFTER CURATION ONLY | Regionally relevant candidate. Dataset-specific inspection and geographic/date compatibility with the 20 project districts remain unresolved. |
| GSI Landslide Hazard Study resources | C. SUPPORTING ONLY | Official GSI resources expose hazard-study material, not a dated machine-readable J&K event inventory. |
| NDMA Landslide page and reports | C. SUPPORTING ONLY | Official guidance and hazard-zonation context; no dated event table. |
| JKSDMA | D. NOT SUITABLE FOR LABELS IN THIS RUN | Public site was under maintenance; no event dataset was accessible. |
| Zenodo/repository searches | D. NOT SUITABLE FOR LABELS IN THIS RUN | Results included susceptibility products or inventories from other regions; no verified J&K project-period event source was accepted. |

## Successfully obtained files

- `data/raw/disasters/landslide_sources/NASA_Global_Landslide_Catalog_Export_rows.csv`: 11,033-record NASA extract preserved for provenance.
- `data/raw/disasters/landslide_inventory.csv`: empty evidence-only inventory with the required schema. It contains no fabricated or unverified records.
- `data/raw/disasters/landslide_sources.csv`: source registry and classifications.

## Findings

- Candidate records inspected: **11,033** in the NASA export.
- Candidate India records: **1,265**.
- Candidate J&K bounding-box records: **201**.
- Candidate project-period records: **0**.
- Project-district records accepted: **0**.
- Inventory records written: **0**.
- Date coverage in the inspected NASA extract: `2007-03-12` to `2017-09-28`.
- Event dates: available in the NASA extract.
- Coordinates: available in the NASA extract.
- Event descriptions/location fields: available in the NASA extract.
- Trigger/cause: available in the NASA extract where reported.
- Severity/impact: partial, including fatality and injury fields where reported.
- District values: not accepted from the NASA extract for the requested period; no coordinate-to-district mapping was performed.

## Geography rule

No district was guessed from a place name or coordinate. A future source may be mapped to districts only with a documented boundary dataset and deterministic point-in-polygon method. That process has not been performed here because there were no eligible project-period NASA records and no verified alternative event inventory was obtained.

## License and usage

The NASA extract is from NASA Open Data and is preserved with its source URL. Current Earthdata services may require an Earthdata login for some downloads or tools. GSI, NDMA, and JKSDMA sources are government resources with source-specific usage policies; no event data was copied from them. The source registry records these limitations.

## Validation

- Inventory schema: valid.
- Inventory records: 0.
- Duplicate event IDs: 0.
- Duplicate event-date-coordinate combinations: 0.
- Missing dates in inventory: 0.
- Missing districts in inventory: 0.
- Missing coordinates in inventory: 0.
- Synthetic records: none.
- Weather labels created: no.
- Weather files modified: no.
- Flood files modified: no.
- ML models trained: no.

Validation command: `python scripts/validate_landslide_research.py`.

## Final decision

**INSUFFICIENT — NO VERIFIED PROJECT-PERIOD LANDSLIDE LABEL DATA FOUND**

The next defensible step is to request or obtain a dated GSI/JKSDMA/official district event register, or to inspect a specific High Mountain Asia inventory with documented event dates and coordinates. Do not proceed to landslide label design until such a source is verified.
