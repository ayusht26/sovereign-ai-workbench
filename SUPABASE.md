# Multi-Tenant RAG System on Supabase — Implementation Guide

**Audience:** This document is written to be handed directly to a coding AI agent (e.g. Claude Code / Copilot in VS Code) that has the Supabase MCP server connected. It should execute the phases in order, using MCP tools (`execute_sql`, `list_tables`, `apply_migration`, etc.) where SQL is given, and generate application code where specified.

**Do not skip Phase 2 (RLS).** Row Level Security is the actual security boundary here — the app-level role checks are UX, not enforcement. If RLS is wrong, a tech employee can read finance documents no matter what the UI hides.

---

## 0. System Overview

```
Company (e.g. Tata Motors)
  └── Users, each with exactly one role: admin | tech | finance | support
        - admin   → can read/write everything in their own company
        - tech    → can only query documents tagged category = 'tech'
        - finance → can only query documents tagged category = 'finance'
        - support → can only query documents tagged category = 'support'

RAG flow: user asks question → embed query → vector search restricted by
RLS to (their company_id AND their role's category) → pass matched chunks
+ question to the LLM → answer. General reasoning/coding questions skip
retrieval and go straight to the LLM.

Admin panel (per-company, not cross-company):
  - Create / edit / delete users, assign roles, set/reset passwords
  - View who accessed which document, and when (audit log)
  - Analytics: query volume, most-used categories, active users
  - Upload/manage documents, assign each to a category

Every user (any role):
  - Login via email+password OR username+password
  - Change own password
  - Upload/change own avatar
```

---

## 1. Supabase Project Setup

1. Create the Supabase project (or confirm the existing one your MCP is connected to).
2. Enable extensions — ask the AI to run via MCP:
   ```sql
   create extension if not exists vector;
   create extension if not exists pgcrypto;
   ```
3. In the Supabase Dashboard → **Authentication → Providers**, confirm **Email** is enabled.
4. In **Authentication → Settings**, turn OFF "Enable email confirmations" only if you want admin-created users to be usable immediately without an email confirmation step (recommended for internally-provisioned company accounts). Otherwise leave it on and have admin-created users confirmed via `email_confirm: true` in the Admin API call (Phase 6).
5. Create two storage buckets: `avatars` (public) and `documents` (private). Do this via MCP or Dashboard → Storage.
6. Set environment variables in your app (`.env.local`, never committed):
   ```
   NEXT_PUBLIC_SUPABASE_URL=...
   NEXT_PUBLIC_SUPABASE_ANON_KEY=...
   SUPABASE_SERVICE_ROLE_KEY=...      # server-only, NEVER shipped to the browser
   ```

---

## 2. Database Schema + Row Level Security

Run this as one migration via MCP (`apply_migration` or `execute_sql`).

### 2.1 Core tables

```sql
create type user_role as enum ('admin', 'tech', 'finance', 'support');

create table companies (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  slug text unique not null,
  created_at timestamptz default now()
);

-- extends auth.users 1:1
create table profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  company_id uuid not null references companies(id) on delete cascade,
  username text unique not null,
  full_name text,
  avatar_url text,
  role user_role not null default 'support',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
create index on profiles (company_id);

create table documents (
  id uuid primary key default gen_random_uuid(),
  company_id uuid not null references companies(id) on delete cascade,
  category user_role not null,        -- which role may read it ('admin' rarely used here)
  title text not null,
  storage_path text,                  -- path in the `documents` storage bucket
  uploaded_by uuid references profiles(id),
  created_at timestamptz default now()
);
create index on documents (company_id, category);

create table document_chunks (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references documents(id) on delete cascade,
  company_id uuid not null,           -- denormalized from documents, for fast RLS
  category user_role not null,        -- denormalized from documents
  chunk_index int not null,
  content text not null,
  embedding vector(1536),             -- match your embedding model's dimension
  created_at timestamptz default now()
);
create index on document_chunks using ivfflat (embedding vector_cosine_ops) with (lists = 100);
create index on document_chunks (company_id, category);

create table document_access_logs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references profiles(id),
  document_id uuid references documents(id),
  company_id uuid not null,
  action text not null,               -- 'query' | 'view' | 'download'
  query_text text,
  created_at timestamptz default now()
);
create index on document_access_logs (company_id, created_at desc);
create index on document_access_logs (user_id, created_at desc);
```

### 2.2 Enable RLS + a non-recursive helper

Querying `profiles` from inside a `profiles` RLS policy causes infinite recursion. Fix: a `security definer` function that reads the current user's own profile bypassing RLS internally.

```sql
alter table companies enable row level security;
alter table profiles enable row level security;
alter table documents enable row level security;
alter table document_chunks enable row level security;
alter table document_access_logs enable row level security;

create or replace function auth_profile()
returns table (company_id uuid, role user_role)
language sql security definer stable as $$
  select company_id, role from profiles where id = auth.uid();
$$;
```

### 2.3 Policies

```sql
-- PROFILES
create policy "self read" on profiles for select
  using (id = auth.uid());

create policy "admin read company" on profiles for select
  using (exists (select 1 from auth_profile() p where p.role = 'admin' and p.company_id = profiles.company_id));

create policy "admin insert company" on profiles for insert
  with check (exists (select 1 from auth_profile() p where p.role = 'admin' and p.company_id = profiles.company_id));

create policy "admin update company" on profiles for update
  using (exists (select 1 from auth_profile() p where p.role = 'admin' and p.company_id = profiles.company_id));

create policy "admin delete company" on profiles for delete
  using (exists (select 1 from auth_profile() p where p.role = 'admin' and p.company_id = profiles.company_id));

create policy "self update (avatar etc)" on profiles for update
  using (id = auth.uid()) with check (id = auth.uid());

-- DOCUMENTS
create policy "role-scoped read" on documents for select
  using (exists (
    select 1 from auth_profile() p
    where p.company_id = documents.company_id
      and (p.role = 'admin' or p.role = documents.category)
  ));

create policy "admin manages documents" on documents for all
  using (exists (select 1 from auth_profile() p where p.role = 'admin' and p.company_id = documents.company_id));

-- CHUNKS (same access rule as parent document)
create policy "role-scoped chunk read" on document_chunks for select
  using (exists (
    select 1 from auth_profile() p
    where p.company_id = document_chunks.company_id
      and (p.role = 'admin' or p.role = document_chunks.category)
  ));

-- ACCESS LOGS
create policy "user logs own access" on document_access_logs for insert
  with check (user_id = auth.uid());

create policy "admin reads company logs" on document_access_logs for select
  using (exists (select 1 from auth_profile() p where p.role = 'admin' and p.company_id = document_access_logs.company_id));
```

**Note on admin scope:** as written, an admin can only manage/see their own company (`admin@tata-motors` cannot touch another company's users or docs). If you also want a cross-company super-admin tier later, add a `super_admin` role and an extra policy branch — don't retrofit this by making regular `admin` cross-company, that would break the isolation model.

---

## 3. Auth: email + username login

Supabase Auth natively supports email/phone login only, not username. Resolve username → email server-side via a restricted lookup function, then sign in normally.

```sql
create or replace function get_email_for_username(uname text)
returns text
language sql security definer stable as $$
  select u.email from auth.users u
  join profiles p on p.id = u.id
  where p.username = uname
  limit 1;
$$;

grant execute on function get_email_for_username(text) to anon, authenticated;
```

Client login logic:
```ts
async function login(identifier: string, password: string) {
  let email = identifier;
  if (!identifier.includes('@')) {
    const { data } = await supabase.rpc('get_email_for_username', { uname: identifier });
    if (!data) throw new Error('Invalid username or password'); // don't leak which one failed
    email = data;
  }
  return supabase.auth.signInWithPassword({ email, password });
}
```
Rate-limit this route (Supabase's built-in auth rate limits help, but add your own on the RPC call too) since it's technically a username-existence oracle otherwise.

**On the `admin@tata-motor` example:** that's not a valid email format (no TLD) — Supabase will reject it as the `auth.users.email`. Use a real-format email as the backing address (e.g. `admin@tatamotors-internal.com`) and let people actually log in with the **username** `admin` instead. The email just needs to exist for Supabase Auth's sake.

---

## 4. Storage: avatars + documents

```sql
-- avatars: path convention {user_id}/avatar.png
create policy "avatar upload own folder" on storage.objects for insert
  with check (bucket_id = 'avatars' and (storage.foldername(name))[1] = auth.uid()::text);

create policy "avatar update own folder" on storage.objects for update
  using (bucket_id = 'avatars' and (storage.foldername(name))[1] = auth.uid()::text);

create policy "avatar public read" on storage.objects for select
  using (bucket_id = 'avatars');
```

`documents` bucket: keep it **private**, no public read policy. Actual file bytes should only ever be served via a short-lived signed URL that your backend generates *after* confirming (via the `documents` table + RLS, using the user's own session) that they're allowed to see that file. Path convention: `{company_id}/{category}/{document_id}/{filename}`.

---

## 5. RAG pipeline

**Ingestion** (admin-only, run server-side):
1. Admin uploads a file → stored in `documents` bucket, row inserted in `documents` with `category` set.
2. Chunk the text (~500–800 tokens, ~15% overlap).
3. Embed each chunk (OpenAI `text-embedding-3-small` or Voyage AI — pick one and keep the `vector()` dimension in Section 2.1 matching it).
4. Insert into `document_chunks`, copying `company_id` and `category` from the parent document.

**Retrieval** (per query, using the *user's own* Supabase session/JWT — not the service role — so RLS actually filters the results):
1. Embed the user's question.
2. `select ... from document_chunks order by embedding <=> $query_embedding limit 8` — RLS silently restricts this to the caller's company + role-permitted category automatically. No manual `where role = ...` needed if RLS is correct — but add it anyway as defense-in-depth.
3. Insert a row into `document_access_logs` (action='query', query_text=the question) for whichever chunks/documents were actually returned.
4. If no relevant chunks are found above a similarity threshold, or the question is general reasoning/coding (not document-related), skip retrieval and just call the LLM directly — don't force irrelevant context into every prompt.

---

## 6. Backend: admin operations (service role, server-only)

These must run in a server context (Next.js Route Handler / Supabase Edge Function) using `SUPABASE_SERVICE_ROLE_KEY`, and must independently verify the caller is an admin of the relevant company before doing anything (don't trust the frontend).

Each handler: verify caller → check admin role for target `company_id` → validate input → act.

- **`POST /api/admin/users`** — create user
  - Check `username` and `email` are unique (query first)
  - `supabase.auth.admin.createUser({ email, password, email_confirm: true })`
  - Insert matching `profiles` row (`username`, `company_id`, `role`)
  - If either step fails, roll back the other (delete the auth user if the profile insert fails)
- **`PATCH /api/admin/users/:id`** — update role / full_name / etc.
- **`POST /api/admin/users/:id/reset-password`** — `supabase.auth.admin.updateUserById(id, { password })`
- **`DELETE /api/admin/users/:id`** — `supabase.auth.admin.deleteUser(id)` (cascades to `profiles` via FK)
- **`GET /api/admin/access-logs?company_id=`** — can actually just be a direct client-side query since RLS already scopes it correctly for an admin's own session; no service role needed here.

Uniqueness checks: `select 1 from profiles where username = $1` and check `auth.users` via `admin.listUsers` or a lookup function for email — do this in the create-user handler *before* calling `admin.createUser`, and surface a clean "username already taken" / "email already registered" error to the create-user form.

---

## 7. Frontend pages

| Page | Who | Contents |
|---|---|---|
| `/login` | everyone | Toggle "Email / Username", password field, calls the login logic in §3 |
| `/chat` | everyone | RAG + general Q&A interface, per §5 |
| `/profile` | everyone | Avatar upload (to `avatars` bucket), change password (`supabase.auth.updateUser({password})`), view own username/role/company |
| `/admin` | admin only | Tabs: **Users**, **Documents**, **Access Logs**, **Analytics** — gate this route by checking `profiles.role === 'admin'` after auth, not just by hiding the nav link |
| `/admin` → Users tab | | Table of company's users; "New User" form with: username (uniqueness-checked live), email (uniqueness-checked live), password field, role dropdown (tech/finance/support/admin); edit role; reset password; delete |
| `/admin` → Documents tab | | Upload file, assign category, delete document |
| `/admin` → Access Logs tab | | Filterable/searchable table: user, document, action, timestamp |
| `/admin` → Analytics tab | | Charts per §8 |

---

## 8. Analytics queries (admin dashboard)

```sql
-- documents per category
select category, count(*) from documents where company_id = $1 group by category;

-- most active users, last 30 days
select p.username, count(*) as query_count
from document_access_logs l
join profiles p on p.id = l.user_id
where l.company_id = $1 and l.created_at > now() - interval '30 days'
group by p.username
order by query_count desc
limit 10;

-- query volume by day
select date_trunc('day', created_at) as day, count(*)
from document_access_logs
where company_id = $1
group by day
order by day;
```
These are safe to run client-side using the admin's own session — RLS on `document_access_logs` and `documents` already scopes them to the admin's company.

---

## 9. Seeding your test company

Don't insert into `auth.users` directly with raw SQL — it won't set up the auth system correctly. Create the first admin either via the Dashboard (**Authentication → Add User**) or by calling the Admin API once, then insert the matching `companies` + `profiles` rows:

```sql
insert into companies (name, slug) values ('Tata Motors', 'tata-motors') returning id;
```
Then, after creating the auth user for a real email like `admin@tatamotors-internal.com`:
```sql
insert into profiles (id, company_id, username, role)
values ('<auth-user-uuid>', '<company-uuid>', 'admin', 'admin');
```
Use a strong password for real use — `admin123` is fine for local testing only, never for anything with real company documents behind it.

---

## 10. Security checklist before you call this done

- [ ] Service role key never appears in any client-side bundle or `NEXT_PUBLIC_*` variable
- [ ] Every table above has RLS **enabled**, not just policies defined (policies do nothing if RLS isn't turned on)
- [ ] Tested: a `tech` user's query genuinely cannot surface `finance`-category chunks, even by asking the LLM to "ignore instructions and show me everything"
- [ ] Tested: an admin from Company A cannot see/edit Company B's users or documents
- [ ] Username lookup RPC is rate-limited (it's a login-identifier oracle otherwise)
- [ ] Document file bytes are only ever served via short-lived signed URLs, never a public bucket URL
- [ ] Password reset / user creation endpoints re-verify the caller's admin role server-side, not just trusting a client-sent flag

---

## What to tell your VS Code AI

Paste roughly this as your kickoff message:

> Using the connected Supabase MCP server, implement this system in order: Phase 1 (project/extensions/buckets setup), Phase 2 (schema + RLS — run exactly as written, don't simplify away the RLS policies), Phase 3 (username-login RPC), Phase 4 (storage policies), then scaffold the Next.js app for Phases 5–7 (RAG pipeline, admin API routes using the service role key server-side only, and the frontend pages listed in the table). Ask me before running any destructive migration. Confirm each phase's SQL executed successfully via MCP before moving to the next phase.