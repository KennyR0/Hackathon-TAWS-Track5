alter table public.conversations
    add column if not exists openai_conversation_id text null;

create unique index if not exists conversations_openai_conversation_id_key
    on public.conversations (openai_conversation_id)
    where openai_conversation_id is not null;

comment on column public.conversations.openai_conversation_id is
    'Server-side OpenAI Conversations API identifier; never exposed to browser clients.';
