-- Synthetic-development records only. No verified disaster label table is created here.
create table if not exists public.prediction_runs (
    id uuid primary key,
    mode text not null check (mode in ('historical_replay', 'live')),
    source text not null,
    feature_reference_date date not null,
    target_date date not null,
    label_scope text not null check (label_scope = 'SYNTHETIC_DEVELOPMENT_ONLY'),
    created_at timestamptz not null,
    payload jsonb not null
);

create table if not exists public.development_alerts (
    id text primary key,
    run_id uuid not null references public.prediction_runs(id) on delete cascade,
    district text not null,
    hazard text not null check (hazard in ('flood', 'heavy_rain', 'landslide', 'heatwave', 'coldwave', 'windstorm')),
    score double precision not null,
    threshold double precision not null,
    status text not null check (status = 'DEVELOPMENT_SIGNAL_NOT_FOR_DISPATCH'),
    label_scope text not null check (label_scope = 'SYNTHETIC_DEVELOPMENT_ONLY'),
    created_at timestamptz not null,
    payload jsonb not null
);

comment on column public.development_alerts.score is 'Raw uncalibrated estimator score on 0-1 scale; not a probability.';
comment on column public.development_alerts.threshold is 'Validation-selected raw-score threshold on 0-1 scale.';

create table if not exists public.allocation_runs (
    id uuid primary key,
    prediction_run_id uuid not null references public.prediction_runs(id) on delete cascade,
    inventory_scope text not null check (inventory_scope = 'SIMULATED_DEVELOPMENT_ONLY'),
    created_at timestamptz not null,
    payload jsonb not null
);

alter table public.prediction_runs enable row level security;
alter table public.development_alerts enable row level security;
alter table public.allocation_runs enable row level security;

-- No anon/public policies: writes are server-side only with a secret key.
