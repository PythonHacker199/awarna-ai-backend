-- Website push reminders. Run once in Supabase: SQL Editor -> New query -> Run.
-- Each browser that turns reminders on stores only dates and counts here,
-- never document names. Users can only see and change their own rows.

create table if not exists public.push_reminders (
  id           bigint generated always as identity primary key,
  user_id      uuid not null references auth.users (id) on delete cascade,
  endpoint     text not null,          -- the browser's push address
  subscription jsonb not null,         -- the browser's push keys
  remind_on    date not null,          -- the day to send the reminder
  lead_days    int  not null,          -- 30, 7, 1 or 0 days before
  papers       int  not null default 1,
  created_at   timestamptz not null default now()
);

create index if not exists push_reminders_remind_on on public.push_reminders (remind_on);
create index if not exists push_reminders_endpoint  on public.push_reminders (endpoint);

alter table public.push_reminders enable row level security;

drop policy if exists "Own reminders only" on public.push_reminders;
create policy "Own reminders only" on public.push_reminders
  for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);
