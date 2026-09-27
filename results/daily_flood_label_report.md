# Daily Flood Dataset Report

## Construction
Built from `weather_features.csv` (1,022,880 hourly rows) and the curated IFI event file. The weather data was aggregated to 42,620 district-day rows.

Aggregation rules:
- precipitation_daily_sum: precipitation sum
- rain_daily_sum: rain sum
- snowfall_daily_sum: snowfall sum
- temperature_2m_daily_mean: temperature_2m mean
- temperature_2m_daily_min: temperature_2m min
- temperature_2m_daily_max: temperature_2m max
- relative_humidity_2m_daily_mean: relative_humidity_2m mean
- relative_humidity_2m_daily_max: relative_humidity_2m max
- wind_speed_10m_daily_mean: wind_speed_10m mean
- wind_speed_10m_daily_max: wind_speed_10m max
- wind_gusts_10m_daily_max: wind_gusts_10m max
- soil_moisture_0_to_7cm_daily_mean: soil_moisture_0_to_7cm mean
- soil_moisture_7_to_28cm_daily_mean: soil_moisture_7_to_28cm mean
- soil_moisture_28_to_100cm_daily_mean: soil_moisture_28_to_100cm mean
- soil_temperature_0_to_7cm_daily_mean: soil_temperature_0_to_7cm mean
- soil_temperature_7_to_28cm_daily_mean: soil_temperature_7_to_28cm mean
- soil_temperature_28_to_100cm_daily_mean: soil_temperature_28_to_100cm mean
- snow_depth_end_of_day: snow_depth last
- precipitation_3h_end_of_day: precipitation_3h last
- precipitation_6h_end_of_day: precipitation_6h last
- precipitation_12h_end_of_day: precipitation_12h last
- precipitation_24h_end_of_day: precipitation_24h last
- precipitation_3d_end_of_day: precipitation_3d last
- precipitation_7d_end_of_day: precipitation_7d last
- rain_3h_end_of_day: rain_3h last
- rain_6h_end_of_day: rain_6h last
- rain_12h_end_of_day: rain_12h last
- rain_24h_end_of_day: rain_24h last
- rain_3d_end_of_day: rain_3d last
- rain_7d_end_of_day: rain_7d last
- snowfall_24h_end_of_day: snowfall_24h last
- snowfall_3d_end_of_day: snowfall_3d last
- snowfall_7d_end_of_day: snowfall_7d last
- snow_depth_change_24h_end_of_day: snow_depth_change_24h last
- temperature_mean_6h_daily_mean: temperature_mean_6h mean
- temperature_mean_12h_daily_mean: temperature_mean_12h mean
- temperature_mean_24h_daily_mean: temperature_mean_24h mean
- temperature_min_24h_daily_min: temperature_min_24h min
- temperature_max_24h_daily_max: temperature_max_24h max
- temperature_min_3d_daily_min: temperature_min_3d min
- temperature_max_3d_daily_max: temperature_max_3d max
- humidity_mean_6h_daily_mean: humidity_mean_6h mean
- humidity_mean_12h_daily_mean: humidity_mean_12h mean
- humidity_mean_24h_daily_mean: humidity_mean_24h mean
- humidity_max_24h_daily_max: humidity_max_24h max
- wind_speed_mean_6h_daily_mean: wind_speed_mean_6h mean
- wind_speed_mean_24h_daily_mean: wind_speed_mean_24h mean
- wind_speed_max_24h_daily_max: wind_speed_max_24h max
- wind_gust_max_24h_daily_max: wind_gust_max_24h max
- wind_gust_max_3d_daily_max: wind_gust_max_3d max
- soil_moisture_0_7cm_mean_24h_daily_mean: soil_moisture_0_7cm_mean_24h mean
- soil_moisture_0_7cm_lag_24h_end_of_day: soil_moisture_0_7cm_lag_24h last
- soil_moisture_0_7cm_change_24h_end_of_day: soil_moisture_0_7cm_change_24h last
- soil_moisture_7_28cm_mean_24h_daily_mean: soil_moisture_7_28cm_mean_24h mean
- soil_moisture_7_28cm_lag_24h_end_of_day: soil_moisture_7_28cm_lag_24h last
- soil_moisture_7_28cm_change_24h_end_of_day: soil_moisture_7_28cm_change_24h last
- soil_moisture_28_100cm_mean_24h_daily_mean: soil_moisture_28_100cm_mean_24h mean
- soil_moisture_28_100cm_lag_24h_end_of_day: soil_moisture_28_100cm_lag_24h last
- soil_moisture_28_100cm_change_24h_end_of_day: soil_moisture_28_100cm_change_24h last
- soil_temperature_0_7cm_mean_24h_daily_mean: soil_temperature_0_7cm_mean_24h mean
- soil_temperature_7_28cm_mean_24h_daily_mean: soil_temperature_7_28cm_mean_24h mean
- soil_temperature_28_100cm_mean_24h_daily_mean: soil_temperature_28_100cm_mean_24h mean
- precipitation_lag_1h_end_of_day: precipitation_lag_1h last
- precipitation_lag_3h_end_of_day: precipitation_lag_3h last
- precipitation_lag_6h_end_of_day: precipitation_lag_6h last
- precipitation_lag_24h_end_of_day: precipitation_lag_24h last
- temperature_lag_24h_end_of_day: temperature_lag_24h last
- weather_code_mode: daily mode; categorical codes are never averaged
- Hourly calendar/cyclical features were omitted; calendar fields can be derived directly from `date`.
- Lag and rolling features are retained as end-of-day values because they represent the information available at the final hour of that date; they are not treated as daily sums.

## Label semantics
- `VERIFIED_FLOOD`: 32 district-date combinations supported by explicit IFI flood records.
- `NO_VERIFIED_EVENT`: 42588 district-days without a verified event record. These are **unknown/not-established**, not confirmed flood negatives; `flood_event_label` remains missing for them.
- Exactly 32 positive combinations were normalized from 29 source event records.
- No dates before or after a documented event date were expanded.

## Coverage
- Districts in weather data: 20
- Districts with verified flood events: 15 (Anantnag, Bandipora, Baramulla, Budgam, Doda, Ganderbal, Kathua, Kishtwar, Kupwara, Poonch, Pulwama, Rajouri, Ramban, Samba, Shopian)
- Date range: 2020-01-01 to 2025-10-31
- Positive district-days per district: {'Anantnag': 5, 'Bandipora': 1, 'Baramulla': 1, 'Budgam': 2, 'Doda': 1, 'Ganderbal': 3, 'Kathua': 3, 'Kishtwar': 2, 'Kupwara': 3, 'Poonch': 3, 'Pulwama': 1, 'Rajouri': 3, 'Ramban': 2, 'Samba': 1, 'Shopian': 1}
- Multiple positive event records on the same date: {Timestamp('2020-04-27 00:00:00'): 2, Timestamp('2021-07-28 00:00:00'): 3, Timestamp('2021-09-09 00:00:00'): 2, Timestamp('2022-07-20 00:00:00'): 2, Timestamp('2022-08-11 00:00:00'): 2, Timestamp('2023-07-15 00:00:00'): 2}

## Missing values
Total missing cells: 128,544. Missing values are retained from feature warm-up windows and from the intentionally unknown flood labels.

## Validation
- Duplicate district-date combinations: 0.
- Verified positive district-date combinations: 32 (expected 32).
- Raw Open-Meteo file modification timestamps were unchanged during execution.
- No ML model was trained.
- No synthetic flood labels were created.
- No event dates were expanded beyond the documented event date.

## Limitation
The verified event source covers only part of the weather period and only 15 districts in the explicit-event subset. An unrecorded date is not established as flood-free. This daily dataset is therefore appropriate for documented positive-event analysis, not for treating all remaining rows as confirmed negatives.

Missing-value columns:
- `flood_event_ids`: 42,588
- `flood_event_label`: 42,588
- `label_source_url`: 42,588
- `rain_7d_end_of_day`: 120
- `precipitation_7d_end_of_day`: 120
- `snowfall_7d_end_of_day`: 120
- `snowfall_3d_end_of_day`: 40
- `precipitation_3d_end_of_day`: 40
- `rain_3d_end_of_day`: 40
- `temperature_max_3d_daily_max`: 40
- `temperature_min_3d_daily_min`: 40
- `wind_gust_max_3d_daily_max`: 40
- `snow_depth_change_24h_end_of_day`: 20
- `soil_moisture_7_28cm_lag_24h_end_of_day`: 20
- `soil_moisture_0_7cm_change_24h_end_of_day`: 20
- `soil_moisture_0_7cm_lag_24h_end_of_day`: 20
- `soil_moisture_7_28cm_change_24h_end_of_day`: 20
- `precipitation_lag_24h_end_of_day`: 20
- `soil_moisture_28_100cm_change_24h_end_of_day`: 20
- `soil_moisture_28_100cm_lag_24h_end_of_day`: 20
- `temperature_lag_24h_end_of_day`: 20
