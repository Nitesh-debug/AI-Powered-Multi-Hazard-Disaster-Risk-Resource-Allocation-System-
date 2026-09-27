# Limitations

- Six models reproduce Phase 7A synthetic development rules, not verified disaster outcomes. Phase 7F scores are raw and uncalibrated.
- Verified flood examples available to the project are positive-only: 32 verified positive district-days, zero verified negative district-days, and 42,588 unknown of 42,620 rows. Unknown is not a negative. Other hazards have no accepted verified labels.
- Phase 7E and 7F evaluated the same 2023-01-01 through 2025-10-31 interval; this is not a project-wide pristine holdout. Districts repeat through time; spatial transfer is untested.
- Live provider coverage has not been verified across all 20 districts. One provider failure is isolated to its district, but upstream access may still fail broadly.
- Demo weather is fixed, perturbed fixture data, not current or observed weather.
- Simulated population, exposure, vulnerability, facilities, supplies, capacities, suitability, and travel estimates are invented solely for software demonstration and cannot be treated as official values.
- There is no road routing, real-time stock synchronization, dispatch, SMS/email, user authentication, or real public-warning workflow.
- SQLite is local. Supabase integration is optional; no project credentials/account or remote connection test are evidenced.
- Docker execution, remote GitHub Actions execution, and production deployment require separate environment evidence.
- The frontend map shows weather reference points only. No district polygons are inferred.
