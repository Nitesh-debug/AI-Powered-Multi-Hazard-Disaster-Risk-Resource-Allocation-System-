# Phase 4 Consolidated Disaster Data Assessment

## Scope and evidence basis

This assessment inspects the existing six disaster research tracks and their reports/summaries. It does not collect new data, create labels, modify weather/flood/other research outputs, merge datasets, or train models.

The project has complete weather inputs and engineered weather features for 20 districts from `2020-01-01` through `2025-10-31`. Disaster evidence is not equally complete across the six tracks.

## Consolidated assessment

| Disaster | Label status | Verified events | District coverage | Date coverage | Supervised labels now? |
| --- | --- | ---: | --- | --- | --- |
| Flood | `VERIFIED_LABELS_AVAILABLE` | 32 district-days | 15 districts | 2020-04-27 to 2023-08-18 | No: positives exist, but unknown days are not confirmed negatives |
| Landslide | `ADDITIONAL_HISTORICAL_DATA_REQUIRED` | 0 | 0 project-period districts | No accepted project-period records | No |
| Heatwave | `ADDITIONAL_HISTORICAL_DATA_REQUIRED` | 0 | 0 project-period districts | No candidate event dates | No |
| Coldwave | `ADDITIONAL_HISTORICAL_DATA_REQUIRED` | 0 | 0 project-period districts | No candidate event dates | No |
| Windstorm | `CRITERIA_BASED_LABELING_POSSIBLE_AFTER_DATA_ACQUISITION` | 0 event records | 0 event districts; 15 relevant NOAA stations | No event dates | No |
| Heavy Rain | `CRITERIA_BASED_LABELING_POSSIBLE_AFTER_DATA_ACQUISITION` | 0 event records | 0 event districts | No event dates | No |

The detailed machine-readable assessment is in `phase4_disaster_data_assessment.csv`.

## Track findings

### Flood

The frozen flood pipeline contains 29 explicit IFI flood records normalized to 32 verified district-date combinations across 15 districts. The daily flood dataset has 42,620 district-days, of which 32 are verified positives and 42,588 are `NO_VERIFIED_EVENT` unknowns. That distinction is correct: no event record does not establish that a day was flood-free.

The flood evidence supports further review of a documented event-day alignment. It does not support expanding an event to adjacent dates or hours, filling all unknowns with zero, or claiming balanced 2020–2025 ground truth. The daily flood dataset and its source provenance remain frozen.

### Landslide

The NASA catalog inspection covered 11,033 records, including 201 J&K-bounding-box records, but no records in the 2020–2025 target period. No project-period district records were accepted and no coordinate-to-district guesses were made. Additional dated event data is required before label design.

Rainfall, soil moisture, terrain, and slope variables remain inputs or possible contextual features; they are not landslide labels.

### Heatwave

No verified J&K project-period heatwave event records were obtained. IMD criteria were documented, but applying them requires appropriate station observations, normal maximum temperatures, terrain/region classification, and any operational duration metadata. The Open-Meteo district points are not IMD station records and were not used as labels.

### Coldwave

No verified J&K project-period coldwave event records were obtained. The relevant IMD approach is station-based and requires minimum temperature, normal minimum temperature, departure from normal, and appropriate regional/terrain handling. These inputs and official event declarations were not obtained.

### Windstorm

No dated J&K windstorm event records were obtained. NOAA ISD station metadata identified 15 Indian stations in the J&K bounding area, and the observation product can provide wind speed, direction, gust, and maximum gust. Those are observations, not event labels. A later phase must define the event taxonomy and approved severe-wind criterion while keeping cyclone, squall, gale, thunderstorm-related damaging wind, and generic wind observations separate.

### Heavy Rain

No verified J&K heavy-rain event records were obtained. IMD rainfall services and station data pathways exist, and official terminology was documented: heavy rain `64.5–115.5 mm`, very heavy rain `115.6–204.4 mm`, and extremely heavy rain `204.5 mm or more`, based on the official 24-hour station window. These categories are intensity observations, not automatically event labels. A later phase needs station observations, the correct time window, and deterministic district mapping.

## Scientific distinctions

1. An event label is not the same as a weather observation.
2. Absence of a historical record is not confirmed absence of a disaster.
3. Open-Meteo weather data is an input dataset, not disaster ground truth.
4. NOAA wind observations are observations, not windstorm event labels.
5. IMD rainfall thresholds are official intensity categories, not automatically historical event labels.
6. IMD heatwave and coldwave criteria require appropriate station information and normals where applicable.
7. Landslide labels cannot be manufactured from rainfall, soil moisture, slope, or terrain variables.
8. Flood labels currently contain exactly 32 verified district-date combinations and must not be expanded to undocumented dates or hours.

## Leakage and label-quality risks

| Risk | Current safeguard |
| --- | --- |
| Treating undocumented days as negative labels | Flood daily data uses `NO_VERIFIED_EVENT` with missing label, not confirmed zero. |
| Creating labels from the same weather variables used as inputs | No heatwave, coldwave, windstorm, heavy-rain, or landslide labels were derived from weather. |
| Using future weather information | Weather feature engineering uses past-looking grouped rolling/lag calculations; this assessment does not recompute or alter them. |
| Expanding event labels beyond documented dates | Flood analysis supports event-day combinations only; no adjacent dates/hours were added. |
| Mixing source periods | Each research report records source coverage and target-period limitations. |
| Using old historical events as 2020–2025 labels | NASA landslide records outside the target period were not accepted. |
| Guessing districts | Districts were accepted only when explicitly available or deterministically documented; no unresolved coordinates were assigned. |
| Confusing observations with events | NOAA, IMD, NASA, Copernicus, and Open-Meteo observations are explicitly treated as inputs or possible criteria inputs, not labels. |

## ML readiness

No supervised classification should start immediately for any track as a complete binary problem.

- **Flood:** verified positives are available for further label-work review, but coverage is sparse and unknown days cannot be silently treated as negatives.
- **Windstorm:** criteria-based construction may be possible after obtaining station observations, approving event taxonomy/criterion, and mapping stations deterministically.
- **Heavy Rain:** criteria-based construction may be possible after obtaining official daily station rainfall and the correct 24-hour observation window.
- **Landslide:** additional dated event sources are required before label design.
- **Heatwave:** additional station maxima, normals, terrain classification, and official event/criteria data are required.
- **Coldwave:** additional station minima, normals, regional classification, and official event/criteria data are required.

Potential satellite, reanalysis, terrain, and station datasets can support inputs or contextual features. They do not automatically solve the event-label problem. No final algorithm is selected or implied.

## What we genuinely have today

Today the project has:

- complete hourly Open-Meteo weather inputs and engineered features for 20 districts;
- a frozen daily flood dataset with 32 verified positive district-days and explicit unknown status for unrecorded days;
- observation pathways for wind and rainfall, but no windstorm or heavy-rain event labels;
- official-criteria references for heatwave, coldwave, and rainfall intensity, but not the station observations/normals needed to apply them safely;
- no verified project-period landslide labels;
- no verified project-period heatwave or coldwave labels;
- no verified project-period windstorm or heavy-rain event inventory.

## Neutral next-step plan

1. Keep the flood daily dataset, curated flood records, weather features, and all source inventories frozen.
2. For flood, approve the documented event-day alignment and unknown-label handling before any training design.
3. For windstorm and heavy rain, acquire authorized station observations and define documented criteria/time windows without converting every extreme observation into an event.
4. For heatwave and coldwave, acquire authorized station observations, normals, terrain/region metadata, and official declarations or approved criteria inputs.
5. For landslide, obtain a dated, geographically defensible 2020–2025 event inventory from GSI, JKSDMA, or another verified source.
6. Before ML training, freeze label provenance, validate district/date uniqueness, separate unknown from confirmed negative, and define time-based evaluation without future leakage.

## Validation status

`scripts/validate_phase4_assessment.py` verifies the six sections and the key counts, checks the assessment schema, validates frozen artifact hashes, and confirms that no synthetic labels or training outputs were created by this phase.

No Phase 5 work was started.
