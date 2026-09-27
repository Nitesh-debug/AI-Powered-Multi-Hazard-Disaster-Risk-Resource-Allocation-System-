# Phase 5 ML Dataset Design

## Decision
Phase 5 defines a leakage-aware ML dataset contract but does not materialize a new processed dataset and does not train a model.

The forecast contract is a one-day lead design: features from `feature_reference_date` may be used to predict a target label for `target_date = feature_reference_date + 1 day`. Same-day daily weather can be used only for event-day analysis, not for a forecasting baseline.

## Source and unit
- Source table: `data/processed/daily_flood_dataset.csv`.
- Unit of analysis: one district and one target date.
- Source coverage: 20 districts, `2020-01-01` to `2025-10-31`.
- Source rows: 42,620; one-day-lead eligible target rows: 42,600.

## Label semantics
- `VERIFIED_FLOOD`: 32 district-days with documented flood provenance.
- `NO_VERIFIED_EVENT`: 42,588 district-days whose flood status is unknown/not established.
- Confirmed negative flood labels: 0.
- `NO_VERIFIED_EVENT` must not be converted to `0` for supervised binary training.
- No synthetic labels are introduced by this phase.

## Feature contract
- Baseline shifted weather inputs: 68 columns, listed in `phase5_ml_feature_schema.csv`.
- `district` and `date` are keys, not model inputs.
- `latitude` and `longitude` are optional context after review because sparse labels can make static geography act like district memorization.
- Excluded audit/target columns: `flood_event_label`, `label_status`, `label_source`, `label_source_url`, `flood_event_ids`.
- Any calendar features in Phase 6 must be derived from `feature_reference_date`, not from future target context beyond the requested lead time.

## Temporal split plan
- `train`: target `2020-01-02` to `2021-12-31`, 14,600 district-days, 17 verified positives, 14,583 unknown days, 0 confirmed negatives.
- `validation`: target `2022-01-01` to `2022-12-31`, 7,300 district-days, 8 verified positives, 7,292 unknown days, 0 confirmed negatives.
- `test`: target `2023-01-01` to `2025-10-31`, 20,700 district-days, 7 verified positives, 20,693 unknown days, 0 confirmed negatives.

These splits are chronological and non-overlapping. They are suitable for design validation and future backtesting discipline, but they do not make the current data supervised-binary-ready because the non-positive rows are unknown rather than confirmed negative.

## Phase 6 gate
Before disaster prediction starts, the next phase should either acquire confirmed negative/absence evidence or explicitly choose a method that supports positive-unlabeled or event-retrieval evaluation. Expensive model training remains out of scope until explicitly approved.

## Safeguards
- Raw data is not modified.
- Existing processed data is not modified.
- No historical disaster events are fabricated.
- Label provenance is kept for audit and excluded from model features.
- Target and provenance fields are excluded from model inputs.
- No ML model was trained.
