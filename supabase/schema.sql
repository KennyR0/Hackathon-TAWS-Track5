create table if not exists organizations (
    id text primary key,
    name text not null,
    created_at timestamptz not null default timezone('utc', now())
);

create table if not exists idempotency_keys (
    organization_id text not null,
    operation text not null,
    idempotency_key text not null,
    request_hash text not null,
    response_status integer not null default 200,
    response_body jsonb not null default '{}'::jsonb,
    expires_at timestamptz not null,
    created_at timestamptz not null default timezone('utc', now()),
    primary key (organization_id, operation, idempotency_key)
);

create table if not exists signal_reviews (
    id text primary key,
    signal_id text not null,
    previous_status text not null,
    status text not null,
    justification text not null,
    reviewed_by text not null,
    reviewed_at timestamptz not null,
    created_at timestamptz not null
);

create table if not exists briefings (
    id text primary key,
    organization_id text not null,
    watchlist_id text not null,
    status text not null,
    executive_summary text not null,
    total_signals integer not null,
    pending_review_count integer not null,
    reviewed_count integer not null,
    escalated_count integer not null,
    discarded_count integer not null,
    requires_human_review boolean not null default true,
    disclaimer text not null,
    created_at timestamptz not null,
    updated_at timestamptz not null
);

create table if not exists briefing_signals (
    briefing_id text not null,
    signal_id text not null,
    priority text not null,
    reason text not null,
    suggested_research_actions jsonb not null default '[]'::jsonb,
    position integer not null,
    primary key (briefing_id, signal_id)
);

create table if not exists agent_runs (
    id text primary key,
    organization_id text not null,
    conversation_id text null,
    current_node text not null,
    status text not null,
    model_name text not null,
    prompt_version text not null,
    input_hash text not null,
    started_at timestamptz not null,
    finished_at timestamptz null,
    error_code text null,
    retry_count integer not null default 0
);

create table if not exists agent_run_steps (
    id text primary key,
    run_id text not null references agent_runs(id) on delete cascade,
    node text not null,
    status text not null,
    step_at timestamptz not null,
    payload jsonb not null default '{}'::jsonb
);

create table if not exists agent_run_source_snapshots (
    run_id text not null references agent_runs(id) on delete cascade,
    snapshot_id text not null,
    snapshot_kind text not null,
    primary key (run_id, snapshot_id)
);

create table if not exists audit_events (
    id text primary key,
    organization_id text not null,
    entity_type text not null,
    entity_id text not null,
    event_type text not null,
    payload jsonb not null default '{}'::jsonb,
    created_at timestamptz not null
);

create table if not exists provider_cache (
    id uuid primary key default gen_random_uuid(),
    provider text not null,
    cache_key text not null,
    request_params_hash text not null,
    response_json jsonb not null,
    fetched_at timestamptz not null default timezone('utc', now()),
    expires_at timestamptz not null,
    request_cost integer not null default 1,
    status_code integer not null,
    data_mode text not null,
    content_hash text null,
    created_at timestamptz not null default timezone('utc', now()),
    unique (provider, cache_key)
);

create table if not exists provider_budgets (
    provider text not null,
    period_type text not null,
    max_requests integer not null,
    used_requests integer not null default 0,
    safety_reserve integer not null default 0,
    reset_at timestamptz not null,
    updated_at timestamptz not null default timezone('utc', now()),
    primary key (provider, period_type)
);

create table if not exists provider_health (
    provider text primary key,
    circuit_state text not null default 'closed',
    consecutive_failures integer not null default 0,
    opened_at timestamptz null,
    retry_after timestamptz null,
    last_success_at timestamptz null,
    last_failure_at timestamptz null,
    last_error_code text null,
    last_error_message text null,
    updated_at timestamptz not null default timezone('utc', now())
);

create index if not exists idx_signal_reviews_signal_id
    on signal_reviews (signal_id, created_at);

create index if not exists idx_briefings_watchlist_id
    on briefings (watchlist_id, created_at desc);

create index if not exists idx_agent_runs_status
    on agent_runs (status, started_at desc);

create index if not exists idx_agent_run_steps_run_id
    on agent_run_steps (run_id, step_at);

create index if not exists idx_audit_events_entity
    on audit_events (entity_type, entity_id, created_at);

create index if not exists idx_provider_cache_expires_at
    on provider_cache (expires_at);

create index if not exists idx_provider_health_retry_after
    on provider_health (retry_after);

create or replace function prevent_append_only_mutation()
returns trigger
language plpgsql
as $$
begin
    raise exception 'Table % is append-only', tg_table_name;
end;
$$;

drop trigger if exists trg_signal_reviews_append_only on signal_reviews;
create trigger trg_signal_reviews_append_only
before update or delete on signal_reviews
for each row execute function prevent_append_only_mutation();

drop trigger if exists trg_agent_run_steps_append_only on agent_run_steps;
create trigger trg_agent_run_steps_append_only
before update or delete on agent_run_steps
for each row execute function prevent_append_only_mutation();
