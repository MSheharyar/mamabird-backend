-- The contact form had nowhere to post to, so contact.html composed a
-- mailto: instead. This is the table behind POST /contact.
--
-- Run this in Supabase before deploying the endpoint, or every submission
-- returns 500.

create table if not exists public.contact_messages (
  id          uuid primary key default gen_random_uuid(),
  client_id   uuid not null references public.clients(id) on delete cascade,
  name        text not null,
  email       text not null,
  topic       text not null default 'Other',
  message     text not null,
  handled     boolean not null default false,
  created_at  timestamptz not null default now()
);

-- What the inbox view actually asks for: this client's unhandled
-- enquiries, newest first.
create index if not exists contact_messages_client_created_idx
  on public.contact_messages (client_id, created_at desc);

alter table public.contact_messages enable row level security;

-- No policy is granted to anon or authenticated on purpose. The API writes
-- with the service key; nothing in a browser should ever read this table,
-- because it holds names and addresses of people who wrote in.
