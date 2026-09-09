-- Password reset tokens.
-- Run in the Supabase SQL editor before deploying the reset endpoints.
--
-- The token itself is never stored. We keep only sha256(token), so a dump of
-- this table cannot be used to reset anyone's password.

create table if not exists public.password_resets (
    id          uuid primary key default gen_random_uuid(),
    user_id     uuid not null references public.users (id) on delete cascade,
    token_hash  text not null,
    expires_at  timestamptz not null,
    used_at     timestamptz,
    requested_ip text,
    created_at  timestamptz not null default now()
);

-- Lookup is always by hash, and it must be unique so a collision cannot
-- resolve to two accounts.
create unique index if not exists password_resets_token_hash_idx
    on public.password_resets (token_hash);

-- Used to expire a user's other outstanding tokens when one is consumed,
-- and to rate limit requests per account.
create index if not exists password_resets_user_idx
    on public.password_resets (user_id, created_at desc);

-- The API talks to Supabase with the service key, which bypasses RLS. RLS is
-- enabled with no permissive policy so a leaked anon key cannot read or write
-- reset tokens.
alter table public.password_resets enable row level security;

-- Housekeeping: nothing here is useful once it has expired or been used.
-- Run periodically, or wire to pg_cron if it is available on the instance.
--   delete from public.password_resets
--   where used_at is not null or expires_at < now() - interval '7 days';
