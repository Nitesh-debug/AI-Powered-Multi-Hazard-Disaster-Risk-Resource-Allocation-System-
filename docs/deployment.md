# Deployment

## Local Demo

Prerequisites: Python 3.11, Node.js 22, npm.

~~~powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-api.txt
python -m uvicorn api.main:app --reload --port 8000
~~~

In another terminal:

~~~powershell
cd frontend
npm ci
$env:VITE_API_PROXY_TARGET = "http://127.0.0.1:8000"
npm run dev -- --port 5173
~~~

Use Replay for the fixed historical feature snapshot, Demo for offline SIMULATED_DEMO_WEATHER, and Live only to attempt the external provider. Demo values are fixed and not current weather.

## Docker Compose

With Docker Engine and Compose available: docker compose up --build. The UI binds to loopback port 8080 by default; SQLite uses the api-data volume. Set WEB_PORT to change the port. A local Docker build/run must be separately verified; configuration alone is not evidence that the containers execute successfully.

## Supabase

Without credentials, SQLite remains active. For an authorized project, apply db/migrations/001_phase9_development_schema.sql, then set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in an untracked server-side .env. Startup checks the required PostgREST tables; connection/schema failure disables mirroring and leaves SQLite active. Never place the service-role key in Vite variables or the browser bundle.

## Production Gate

This repository does not provide user authentication, an operational security review, official data, verified no-event labels, production deployment evidence, warning authority, or dispatch integration. Do not deploy publicly or use for real operations on the basis of this demo.
