# Phase 6 Label Strategy

## Scope

This is Phase 6 preparation only. It does not create labels, modify raw or processed data, create synthetic disaster events, write training code, or train a model.

## Decision

The currently available flood labels are **not sufficient for standard supervised binary ML training or defensible binary evaluation**.

The data contain verified positives, but no verified negatives. `NO_VERIFIED_EVENT` means that a flood was not established by the available event evidence. It does not mean that a flood was verified not to have occurred. Those rows must remain unknown unless separate evidence establishes non-occurrence.

The current labels can support descriptive analysis, source auditing, label-acquisition planning, and later positive-unlabeled research. They cannot yet support a conventional positive-versus-negative flood classifier.

## Evidence from the current artifacts

| Measure | Current availability | Implication |
| --- | ---: | --- |
| District-date rows | 42,620 | Full weather panel size is not the labeled sample size. |
| Verified flood district-days | 32 | Positive observations exist. |
| Unique verified event IDs | 29 | Three event IDs cover two districts each, so 32 rows are not 32 independent events. |
| Unique positive dates | 25 | Some positives share dates and may share weather systems. |
| Districts with at least one positive | 15 of 20 | Five districts have no verified positive, which cannot be interpreted as zero flood risk. |
| `NO_VERIFIED_EVENT` rows | 42,588 | These are unknown, not negative. |
| Verified negative district-days | 0 | A binary target cannot be formed without changing label meaning. |
| Positive provenance | 32 rows from one IMD-labelled source and one source URL | Source non-reporting cannot establish event absence. |
| Positive date range | 2020-04-27 to 2023-08-18 | The weather panel continues through 2025-10-31, but later rows have no verified positive evidence in this dataset. |
| Phase 5 baseline weather inputs | 68 | The candidate feature count is far too large relative to the number of independent positive events. |

If every unknown row were incorrectly treated as negative, the apparent positive fraction would be only 0.0751%, with about 1,331 unknown rows per verified positive. That calculation describes the label table only. It is not an estimate of flood prevalence and must not be used to justify negative labels.

### Current temporal split feasibility

| Split | Verified positive district-days | Unique event IDs | Unknown rows | Verified negatives | Binary-ready |
| --- | ---: | ---: | ---: | ---: | --- |
| Train, target years 2020-2021 | 17 | 14 | 14,583 | 0 | No |
| Validation, target year 2022 | 8 | 8 | 7,292 | 0 | No |
| Test, target years 2023-2025 | 7 | 7 | 20,693 | 0 | No |

The planned splits are chronological, but label availability is inadequate in every split. The test interval contains only seven known event IDs, all in 2023. Rows in 2024 and 2025 are unknown and cannot be used as negative test cases.

## Why supervised training is blocked

1. **No negative class:** specificity, false-positive rate, precision, calibration, and operational false-alert burden cannot be measured without verified negatives.
2. **Too few independent positive episodes:** the training period contains only 14 unique event IDs for 68 candidate weather inputs. District-days sharing an event or weather system are correlated and cannot be counted as independent evidence.
3. **Unstable validation and test estimates:** validation has eight unique events and test has seven. At seven independent positives, a worst-case normal approximation gives a 95% margin of error of about 37 percentage points for event-level recall.
4. **Single-source ascertainment:** every positive row uses the same source label and URL. The source proves the listed events, but the current artifacts do not establish complete daily, district-level surveillance from which non-events can be inferred.
5. **Uneven temporal coverage:** verified positives stop in August 2023 while the weather data continue through October 2025. This could reflect source coverage, event incidence, or both.
6. **Uneven spatial coverage:** five districts have no verified positives and several have only one. Random row splitting could make district identity or static coordinates act as a shortcut rather than demonstrate transferable weather-risk learning.

## Required label ontology

Future label work should preserve three mutually exclusive states:

| Label state | Meaning | Eligible for binary training |
| --- | --- | --- |
| `VERIFIED_FLOOD` | A flood occurred in the named district and target period, supported by traceable event evidence. | Positive |
| `VERIFIED_NO_FLOOD` | A competent source explicitly reports no flood, or a demonstrably complete surveillance record confirms no flood for that district and period. | Negative |
| `UNKNOWN` | Available evidence does not establish occurrence or non-occurrence. Existing `NO_VERIFIED_EVENT` rows belong here. | No |

`UNKNOWN` must never be recoded to zero. A weather threshold, low rainfall, a missing news report, or absence from a positive-event catalog is not sufficient evidence for `VERIFIED_NO_FLOOD`.

## Defensible negative-label strategy

### 1. Define the event and observation protocol first

Before reviewing candidate negatives, define:

- The flood types included and excluded, such as riverine, flash, urban, or glacial-lake-related flooding.
- The spatial unit, which remains district.
- The target period, which remains one district-date for the one-day forecast contract.
- How multi-day events, cross-district events, onset, continuation, and cessation are recorded.
- The reporting-delay rule and how later corrections are handled.

The protocol must be fixed before inspecting weather predictors so negative selection is not influenced by the features the model would later use.

### 2. Build a source-coverage matrix

For every candidate source, record district coverage, start and end dates, reporting cadence, expected publication days, missing reports, known outages, revision policy, and whether a closed report includes explicit nil returns.

Suitable primary evidence may include official district emergency-operation or control-room daily logs, disaster-management situation reports, flood-control or irrigation incident bulletins, and complete response or incident registers. A source is eligible to support negatives only when its operating process is capable of recording the flood type and spatial unit in scope.

Hydrological gauges, remote sensing, emergency calls, relief records, and reputable contemporaneous reporting can corroborate a decision. By themselves, low gauge values, no emergency call, no relief payment, or no media report do not prove that no localized flood occurred.

### 3. Admit negatives only through an auditable rule

A district-date may become `VERIFIED_NO_FLOOD` only when one of these conditions is met:

- An authoritative daily record explicitly states no flood or nil flood incidents for that district and date.
- A source with documented mandatory reporting, complete coverage, and no missing or delayed entry has a closed daily record that explicitly supports zero flood incidents.
- An adjudicated combination of independent sources establishes non-occurrence under a pre-registered rule.

If source completeness, district specificity, event type, or date coverage is uncertain, keep the district-date `UNKNOWN`.

Do not infer a negative from the current IMD positive-event source merely because it contains no event entry. First demonstrate that the source is an exhaustive district-day surveillance system for the intended event definition and period.

### 4. Quarantine ambiguous event periods

Do not label controls inside a known event's documented onset-to-cessation interval. Add a reporting-lag buffer based on the source cadence and observed correction delay. If onset, cessation, or reporting delay cannot be established, keep nearby candidate dates unknown rather than inventing an event boundary.

Treat all district-days connected to the same event ID, overlapping event interval, or common documented weather episode as one event group for splitting and uncertainty estimation.

### 5. Sample from verified coverage, not from weather conditions

After non-events are verified, construct the negative pool across the same surveillance regime as the positives. Stratify or probability-sample by district, season or month, year, and source-coverage regime. Include wet and dry verified non-event days.

Do not select negatives because precipitation was low or because their weather differs from positive days. That would define the target using model inputs and create selection bias. Do not use SMOTE or any other synthetic label creation.

Keep the complete verified-negative pool for audit. A later training phase may down-sample verified negatives or use class weights, but evaluation must use a pre-specified representative sample. If a matched case-control evaluation set is used, it cannot estimate real-world precision, calibration, or prevalence without appropriate sampling weights and a defensible population frame.

### 6. Record provenance for every reviewed label

Each future label decision should have, at minimum:

- `district` and `target_date`
- three-state label and event definition version
- event ID or non-event evidence ID
- source organization, document identifier, URL or archive path, and publication date
- source coverage start and end, cadence, and completeness status
- explicit quoted status or structured incident count where licensing permits
- reviewer, review date, and adjudication status
- event-group ID and any exclusion or reporting-lag interval
- immutable source hash or archived snapshot reference where permitted

Use two independent reviews for a sample of negative decisions and all ambiguous decisions. Resolve disagreements before the labels become eligible for training.

## Leakage controls for future dataset construction

### Temporal leakage

- Keep chronological train, validation, and test periods. Never randomly split district-day rows.
- Acquire and review labels using the same protocol across all periods before finalizing the split.
- Keep each event group entirely within one split.
- Fit imputation, scaling, feature selection, thresholds, and any resampling policy on training data only.
- The longest current weather lookback is seven days. Use a seven-day boundary embargo when finalizing validation and test sets so rolling weather windows do not overlap adjacent split boundaries. Confirm the exact embargo from feature lineage before materialization.
- Preserve the Phase 5 one-day lead: predictors end on `feature_reference_date`, and the target is the following day.

### Spatial leakage

- Do not use `district`, event-source identifiers, label provenance, or event IDs as predictors.
- Keep latitude and longitude out of the first baseline. Sparse labels could let them memorize district-specific incidence or reporting intensity.
- Balance negative acquisition across districts and document districts with incomplete surveillance.
- After label expansion, run a secondary district- or region-blocked evaluation in addition to the primary temporal holdout. Do not claim spatial generalization until held-out districts contain enough independent positive and negative evidence.

## Minimum evidence gates before training

There is no universal sample-size threshold for flood prediction. The required size depends on the model complexity and the operational error target. The following are conservative go/no-go planning gates, not guarantees of model validity.

1. Every split must contain both `VERIFIED_FLOOD` and `VERIFIED_NO_FLOOD` observations from documented source coverage.
2. Count independent event groups, not district-day rows, when assessing positive sample size.
3. For a simple interpretable logistic baseline, plan for roughly 10 to 20 independent positive events per effective fitted coefficient. With 14 training event IDs, the current data do not support a 68-feature model or broad feature search.
4. Validation and test should each contain at least 25 independent positive event groups for only a coarse event-recall estimate with a worst-case 95% margin near plus or minus 20 percentage points. About 43 and 97 events are needed for margins near plus or minus 15 and 10 points, respectively, before accounting for clustering.
5. Set the required verified-negative test size from the false-alert target. As a simple benchmark, observing zero false positives among 300 independent verified negatives gives an approximate 95% upper bound near 1% by the rule of three. Consecutive district-days are correlated, so blocked sampling and cluster-aware intervals will require more raw rows.
6. Represent all deployment-relevant districts, seasons, and source-coverage regimes in training. Reserve later chronological periods for untouched evaluation.
7. Recalculate the split plan after verified labels are acquired. Do not preserve the current dates if doing so leaves a split with inadequate events or incomplete source surveillance.

## Evaluation design after the label gate is met

Use event-group and district-aware confidence intervals. Report event-level recall, district-level recall, precision, false-alerts per district-month, and recall at a pre-specified false-alert burden. Accuracy and ROC AUC alone are not suitable for the expected imbalance.

The untouched test set must be evaluated once after model and threshold selection. If verified negatives cannot be obtained at sufficient scale, standard supervised binary training remains blocked. A later phase may separately propose positive-unlabeled learning or event-retrieval ranking, but it must not present unknown rows as negatives or report ordinary binary metrics as if ground-truth negatives existed.

## Phase 6 readiness gate

Phase 6 model development may begin only after all of the following are documented:

- A fixed flood-event definition and three-state label protocol.
- A source-coverage matrix demonstrating where negative verification is possible.
- Auditable `VERIFIED_NO_FLOOD` evidence without recoding unknown rows.
- Enough independent positive event groups and verified negatives in every split for the chosen evaluation precision.
- Event-grouped chronological splits with temporal embargo and a spatial generalization plan.
- A frozen label audit showing that target and provenance fields remain excluded from predictors.

Current status: **blocked for supervised binary ML training**. Continue label acquisition and verification only. No model should be trained from the present label table.
