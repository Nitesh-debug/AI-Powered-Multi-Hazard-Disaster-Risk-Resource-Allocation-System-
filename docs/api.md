# API

Run locally with python -m uvicorn api.main:app --reload --port 8000. Interactive local schema is available at /docs.

| Route | Purpose |
| --- | --- |
| GET /api/health | Runtime, model, fixture, SQLite/Supabase status |
| GET /api/districts | 20 weather reference points; not boundaries or centroids |
| GET /api/registry | Six development model metadata records |
| POST /api/predictions | historical_replay, live, or simulated_demo assessment |
| GET /api/resources[?district=...] | Explicitly simulated resource records |
| GET /api/resources/{resource_id} | One simulated resource record |
| GET /api/exposure[?district=...] | Explicitly simulated exposure/vulnerability rows |
| GET /api/response-plan[?run_id=...] | Plan for a run, or the latest run |
| POST /api/allocations/simulate | Generate and persist a simulated plan |
| POST /api/allocations | Compatibility alias for the simulation route |
| GET /api/alerts | Persisted development threshold signals; no outbound delivery |
| GET /api/runs | Recent persisted runs |

The API has no user authentication or authorization. CORS defaults to the local Vite origins and can be configured with CORS_ORIGINS; request bodies are limited by MAX_REQUEST_BODY_BYTES. Do not expose it publicly without an authenticated reverse proxy, rate limiting, TLS, access controls, and a security review.

All model outputs are synthetic-development, uncalibrated scores. All exposure/resource/travel outputs are simulation-only and not dispatch instructions.
