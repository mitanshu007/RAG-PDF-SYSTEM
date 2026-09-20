create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text,
  full_name text,
  provider text,
  created_at timestamptz not null default now()
);

create table public.documents (
  id uuid primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  filename text not null,
  status text not null check (status in ('queued', 'processing', 'ready', 'failed')),
  created_at timestamptz not null default now()
);

create table public.user_settings (
  user_id uuid primary key references auth.users(id) on delete cascade,
  settings jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

alter table public.profiles enable row level security;
alter table public.documents enable row level security;
alter table public.user_settings enable row level security;

create policy "users can read their profile"
  on public.profiles for select using (auth.uid() = id);
create policy "users can manage their settings"
  on public.user_settings for all using (auth.uid() = user_id);
create policy "users can read their documents"
  on public.documents for select using (auth.uid() = user_id);
