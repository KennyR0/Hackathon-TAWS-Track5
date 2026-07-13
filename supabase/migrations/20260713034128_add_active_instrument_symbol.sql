alter table public.conversations
    add column if not exists active_instrument_symbol text null;

comment on column public.conversations.active_instrument_symbol is
    'Validated symbol from the versioned production universe used for assistant continuity.';
