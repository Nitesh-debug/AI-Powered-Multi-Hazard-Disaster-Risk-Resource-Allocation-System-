# Data And Labels

## Data Classes

- **REAL WEATHER:** historical Open-Meteo-derived project observations/features. Raw and processed source files are not changed by the planning work.
- **VERIFIED REAL EVENTS:** source-supported recorded event days. Current flood evidence is 32 positive district-days across 15 of 20 districts, zero verified negative district-days, and 42,588 unknown days among 42,620 project-period district-days.
- **UNKNOWN:** no verified event record is not evidence of no event. NO_VERIFIED_EVENT is never converted to a negative label.
- **SYNTHETIC DEVELOPMENT LABELS:** deterministic Phase 7A weather rules, explicitly marked SYNTHETIC_DEVELOPMENT_ONLY and version phase7a_v1.
- **SIMULATED RESOURCES / EXPOSURE:** deterministic Phase 9 demonstration scenario, version phase9_simulation_v1; it is not official population, vulnerability, facility, inventory, or capacity data.
- **SIMULATED_DEMO_WEATHER:** deterministic, fixed feature perturbations used only to demonstrate the offline workflow; it is not observed weather.

## Phase 9 Scenario Inventory

The generated scenario contains 140 resources (20 illustrative district nodes for each of seven resource types), 20 population/exposure/vulnerability rows, and 400 ordered district-pair travel-time estimates. Resource coordinates reuse weather lookup points solely as illustrative map nodes; they do not assert a facility exists there. The travel matrix is a heuristic, not a road graph or routed time.

Run python scripts/build_phase9_simulated_scenario.py only when intentionally regenerating the development fixture. Verify reproducibility with python scripts/build_phase9_simulated_scenario.py --check and python scripts/validate_phase9_simulation.py.
