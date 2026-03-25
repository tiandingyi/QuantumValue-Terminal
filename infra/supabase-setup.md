# Supabase Provisioning Runbook

User Story 5 requires manual creation of the Supabase project in the official dashboard.

## 1. Create the Supabase project manually

1. Open the official Supabase dashboard.
2. Create a new project for `QuantumValue Terminal`.
3. Wait until the database and API credentials are ready.

## 2. Export secrets manually in your terminal

Paste these commands into your terminal and replace the placeholder values yourself.
Only sensitive values are exported here.

```bash
export SUPABASE_DB_URL='postgresql://postgres.<project-ref>:<db-password>@<session-pooler-host>:5432/postgres?sslmode=require'
export SUPABASE_DIRECT_DB_URL='postgresql://postgres:<db-password>@<direct-host>:5432/postgres?sslmode=require'

export DATABASE_URL="$SUPABASE_DB_URL"
export MIGRATIONS_DATABASE_URL="${SUPABASE_DIRECT_DB_URL:-$SUPABASE_DB_URL}"
```

Notes:

- `SUPABASE_DB_URL` should use the Supabase `Supavisor session mode` connection string.
- `SUPABASE_DIRECT_DB_URL` is optional for manual troubleshooting and direct-native tools.
- GitHub Actions uses `SUPABASE_DB_URL` for remote initialization because the hosted runner path is more reliable with the session-mode pooler than with the IPv6-only direct host.

## 3. Persist the current exported values into the local `.env`

Run this only after you have exported the real values above.
Non-secret defaults come from `.env.example`.

```bash
cp .env.example .env
cat >> .env <<EOF
SUPABASE_DB_URL=$SUPABASE_DB_URL
SUPABASE_DIRECT_DB_URL=$SUPABASE_DIRECT_DB_URL
DATABASE_URL=$DATABASE_URL
MIGRATIONS_DATABASE_URL=$MIGRATIONS_DATABASE_URL
EOF
```

## 4. Store the same values in GitHub Secrets

Use the GitHub CLI after replacing the placeholder values via `export` above.

Required:

```bash
printf '%s' "$SUPABASE_DB_URL" | gh secret set SUPABASE_DB_URL
```

Optional:

```bash
printf '%s' "$SUPABASE_DIRECT_DB_URL" | gh secret set SUPABASE_DIRECT_DB_URL
```

## 5. Test the Go connection to the remote Supabase instance

From the repository root:

```bash
pnpm --filter api-go db:check
```

Expected result:

- the command exits successfully
- it prints JSON containing `connected_at`, `database`, and `user`
