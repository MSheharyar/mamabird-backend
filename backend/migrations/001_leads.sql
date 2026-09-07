-- Newsletter / lead capture for the marketing site's signup form.
-- Run once against Supabase (SQL Editor) before deploying the /leads router.
--
-- Note: earlier tables were applied by hand through the Supabase dashboard and
-- were never checked in. This is the first migration kept in the repo; number
-- future ones from 002.

create table if not exists public.leads (
    id          uuid primary key default gen_random_uuid(),
    client_id   uuid not null references public.clients (id) on delete cascade,
    email       text not null,
    first_name  text,
    source      text not null default 'unknown',
    created_at  timestamptz not null default now()
);

-- One row per address per tenant: re-subscribing must not create duplicates,
-- and the same address may legitimately exist under a different client.
create unique index if not exists leads_client_email_idx
    on public.leads (client_id, lower(email));

-- Dashboard reads list newest first, scoped to the tenant.
create index if not exists leads_client_created_idx
    on public.leads (client_id, created_at desc);

-- The API talks to Supabase with the service key, which bypasses RLS. RLS is
-- still enabled with no permissive policy so that a leaked anon key cannot
-- read the mailing list.
alter table public.leads enable row level security;
