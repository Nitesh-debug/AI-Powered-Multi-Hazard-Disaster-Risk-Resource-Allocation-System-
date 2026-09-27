# Architecture

## Runtime Path

Historical replay, live Open-Meteo weather, or the clearly marked offline demo-weather fixture produces a prior-day, 68-feature district record. The six Phase 7F estimators return uncalibrated scores for synthetic-development targets. The API adds development signal levels and stores run/signal records in local SQLite. The optional planning engine joins the run to a versioned simulated resource/exposure scenario, ranks districts, then recommends compatible, available capacity within a synthetic travel-time limit. React/Leaflet displays weather reference points and run/planning details.

## Trust Boundaries

- Historical weather features are project inputs; the replay artifact carries no labels.
- Live weather is provider data, but six-hazard model scores remain predictions of synthetic development rules.
- SIMULATED_DEMO_WEATHER is a fixed synthetic fixture and is never a live/replay fallback.
- Verified event labels, unknown/unreported dates, synthetic model targets, simulated exposure, and simulated resource data are separate concepts.
- Resource planning output is SIMULATION_ONLY_NOT_FOR_DISPATCH; there is no public-warning or outbound-notification service.

## Persistence

SQLite is the local source of truth for run, alert, and allocation history. When configured, a server-side Supabase service-role client mirrors those records after a startup schema check; errors preserve the SQLite copy. The versioned planning scenario remains a local development artifact. No browser code receives the service-role key.
