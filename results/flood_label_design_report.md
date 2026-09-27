# Flood Label Design Report

## Scope
This analysis uses only the 29 `EXPLICIT_FLOOD` records from the curated IFI-Impacts v4 subset. It does not read weather values, create labels, or modify any weather dataset.

## What the source provides
The input provides 29 event records dated 2020-04-27 through 2023-08-18. Each record has an event ID, source date, source district text, original cause wording, source, and LGD code field. All records identify IMD as the event source.
There are 3 multi-district records. Their district strings contain explicit project-district names and can be deterministically tokenized into 32 event-date/district combinations without assigning an event to an unlisted district.

## Missing information
The curated input contains no usable start/end duration fields, so duration is unavailable for all 29 records. Severity is missing for 29 records (0 available). Only 2 records contain a non-empty original description/impact text. The source does not establish hourly onset or end times.

## Label strategy recommendation
**Recommend Option A: event-day labeling, subject to a later explicit implementation decision.** For each source event date and each district explicitly listed by that source record, one daily event occurrence is supported. The three multi-district records can be expanded to their listed districts while retaining the same event ID and a multi-district provenance flag.

Option B (event-duration labeling) is not supported because the curated input does not provide event duration. Do not infer duration from weather, neighboring dates, or the `Duration(Days)` field omitted from this curated input.

Option C (event-window labeling) is not recommended for the ground-truth event label. A pre-event or post-event window would be a separate modeling feature/response design and must not be represented as an observed flood date without additional source evidence.

Under the recommended event-day design, the data would produce **32 positive event-date/district combinations** from 29 source records. This report does not create those labels in the hourly weather data.

## Events per district
| district | event_date_combinations |
| --- | --- |
| Anantnag | 5 |
| Bandipora | 1 |
| Baramulla | 1 |
| Budgam | 2 |
| Doda | 1 |
| Ganderbal | 3 |
| Kathua | 3 |
| Kishtwar | 2 |
| Kupwara | 3 |
| Poonch | 3 |
| Pulwama | 1 |
| Rajouri | 3 |
| Ramban | 2 |
| Samba | 1 |
| Shopian | 1 |

## Events per year
| year | event_records |
| --- | --- |
| 2020 | 2 |
| 2021 | 12 |
| 2022 | 8 |
| 2023 | 7 |

## Events per month
| month | event_records |
| --- | --- |
| 3 | 1 |
| 4 | 1 |
| 5 | 3 |
| 7 | 16 |
| 8 | 4 |
| 9 | 3 |
| 10 | 1 |

## Multiple event records on the same date
| date | event_count | event_ids |
| --- | --- | --- |
| 2021-07-28 00:00:00 | 2 | UEI-IMD-FL-2021-0329;UEI-IMD-FL-2021-0330 |
| 2022-07-20 00:00:00 | 2 | UEI-IMD-FL-2022-1125;UEI-IMD-FL-2022-1126 |
| 2022-08-11 00:00:00 | 2 | UEI-IMD-FL-2022-1136;UEI-IMD-FL-2022-1137 |
| 2023-07-15 00:00:00 | 2 | UEI-IMD-FL-2023-0614;UEI-IMD-FL-2023-0615 |

## Multi-district records
| event_id | date | district | district_mapping_status |
| --- | --- | --- | --- |
| UEI-IMD-FL-2020-0147 | 2020-04-27 00:00:00 | Budgam, Shopian | RESOLVED_SOURCE_LIST |
| UEI-IMD-FL-2021-0329 | 2021-07-28 00:00:00 | Anantnag, Bandipora | RESOLVED_SOURCE_LIST |
| UEI-IMD-FL-2021-0333 | 2021-09-09 00:00:00 | Kupwara, Rajouri | RESOLVED_SOURCE_LIST |

## Limitations
The records cover only 2020–2023, omit Jammu, are sparse for supervised learning, and lack hourly timing and severity values. Several source events share dates or affect multiple districts. Any later hourly alignment must document the choice of date boundary and timezone; it must not imply that adjacent hours or dates were observed flood periods.

## Proceed decision
The curated records are sufficient to prototype a documented event-day alignment process, but they are not sufficient to claim complete or balanced flood ground truth for all 20 districts or the full 2020–2025 weather period. No model training should begin until the event-day expansion and handling of missing district/date coverage are approved.