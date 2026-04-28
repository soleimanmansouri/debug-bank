---
id: S03
name: Silent Schema Drift
tier: L3
patterns: [P07, P02, P13]
services: [admin-panel, notification-service, postgres, redis]
---

# S03: Silent Schema Drift

## System Architecture

```
[Admin Panel] --writes--> [Postgres] (notifications table)
                         --publishes--> [pg_notify channel]

[Notification Service] --listens--> [pg_notify channel]
                       --reads--> [Postgres]
                       --caches schema in--> [Redis] (schema:{table} key, 1h TTL)
                       --sends--> [Email/SMS/Push providers]
```

A notification system where admins configure notification templates through the Admin Panel. The Notification Service listens for changes via Postgres LISTEN/NOTIFY, reads the updated config, and dispatches notifications through various channels.

The Notification Service caches the table schema in Redis on startup to dynamically map columns to template variables. This avoids hard-coding column names and lets the team add new template fields without redeploying.

## Setup

- **Admin Panel:** Next.js app, writes directly to Postgres via Prisma ORM
- **Notification Service:** Python, uses `psycopg2` for LISTEN/NOTIFY, SQLAlchemy for reads
- **Postgres:** Single primary, `notifications` table with columns: `id, type, channel, template, recipient_query, active, created_at, updated_at`
- **Redis:** Caches the result of `SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'notifications'` with 1-hour TTL

Recent change: A migration added two new columns to the `notifications` table: `priority` (enum: low/medium/high/critical) and `throttle_seconds` (integer). The Admin Panel was updated to show these fields. The Notification Service was NOT redeployed — the team assumed the dynamic schema cache would pick up the new columns within 1 hour.

## Symptom

Three issues appear over the next 48 hours:

1. **Priority filtering doesn't work.** Admins set notifications to "critical only" but all priorities are sent. No errors in logs.
2. **Throttling doesn't work.** Admins set `throttle_seconds=300` but notifications send without delay. No errors in logs.
3. **Intermittent:** The features randomly start working for ~1 hour, then stop again. The working windows don't correlate with deployments or restarts.

No errors anywhere. All health checks pass. The Admin Panel shows the correct values. Direct database queries confirm the data is correct.

## Red Herrings

### Red Herring 1: Migration Didn't Run on Production
- **Why it looks plausible:** New columns not working = maybe they don't exist in prod.
- **Why it's wrong:** `\d notifications` in psql shows both columns exist with correct types and data.
- **How to falsify:** Query the table directly. Both columns are present and populated.

### Red Herring 2: Notification Service Code Doesn't Handle New Columns
- **Why it looks plausible:** Maybe the code needs to be updated to read `priority` and `throttle_seconds`.
- **Why it's wrong:** The service uses dynamic schema mapping — it reads whatever columns exist. That's the whole point of the schema cache. And the features DO work intermittently.
- **How to falsify:** Read the service code. Column mapping is dynamic via `schema_cache.get_columns('notifications')`. No hardcoded column list.

### Red Herring 3: Prisma ORM Caching Old Schema
- **Why it looks plausible:** Prisma generates a client from the schema. Maybe the generated client doesn't include new columns.
- **Why it's wrong:** The Admin Panel writes correctly (verified by direct DB query). Prisma was regenerated as part of the migration.
- **How to falsify:** Check `prisma/schema.prisma` and `prisma generate` output. Both columns are present.

## Root Cause

**Three problems compose into a single silent failure.**

**Problem 1 — Stale Schema Cache (P07):** The Redis schema cache has a 1-hour TTL. After the migration, the Notification Service continues using the cached schema which doesn't include `priority` or `throttle_seconds`. When it maps columns to template variables, these two columns don't exist in its worldview. It skips them silently — the dynamic mapper treats unknown columns as "not my concern."

This explains why the features randomly work for ~1 hour: when the TTL expires, the service re-reads the schema from `information_schema`, gets the new columns, and everything works. But then...

**Problem 2 — Schema Cache Race (P02):** Two code paths refresh the schema cache:
- **Path A:** TTL expiry → service re-reads from `information_schema` → writes to Redis (correct, includes new columns)
- **Path B:** LISTEN/NOTIFY handler → on any `notifications` table change, refreshes the cache "to stay current" → reads from `information_schema` → writes to Redis

Path B was added 6 months ago as an optimization. But Path B has a bug: it reads from a **connection that was opened before the migration ran.** SQLAlchemy's `information_schema` query uses a cached metadata object tied to the engine's connection pool. Connections created before the migration return the old column list. Connections created after return the new list.

When Path A refreshes (TTL expiry), it may get a new connection → correct schema. When Path B refreshes (on any notification update), it reuses a pooled connection from before the migration → old schema. Path B runs much more frequently (every admin edit) and overwrites Path A's correct cache with stale data.

**Problem 3 — Silent Success (P13):** The dynamic mapper doesn't raise an error when it encounters a column in the data that's not in the schema cache. It silently drops the unknown fields. The notification sends successfully — just without priority filtering or throttling. Monitoring shows 100% success rate because the notification WAS sent. There's no check for "did we apply all configured rules?"

**Pattern composition:**
- **P07 (Stale Config):** Schema cache doesn't reflect the actual database schema.
- **P02 (Multiple Writers):** Two cache refresh paths fight. The stale one wins because it runs more frequently.
- **P13 (Parse Matches Errors as Success):** Silent field dropping means 100% success rate masks total feature failure.

## Investigation Path

1. **Pattern Check:** Features work intermittently on a ~1h cycle → check P07 (stale config with TTL). Features produce no errors but don't work → check P13 (silent success). Two code paths refresh the same cache → check P02 (multiple writers).
2. **Reproduce:** Check Redis: `GET schema:notifications`. Compare column list to actual `information_schema.columns`. If Redis has fewer columns, P07 is confirmed. Wait for TTL expiry, check again — if it's now correct, TTL cycle is confirmed.
3. **Hypothesize:**
   - H1 (correct): Schema cache doesn't include new columns, and something keeps refreshing it with stale data
   - H2 (partial): Connection pool serves pre-migration connections — true but doesn't explain the intermittent fix
   - H3 (wrong): Migration didn't run in production
4. **Isolate:** `MONITOR` Redis for SET operations on `schema:notifications`. Observe two writers. Path A (TTL) writes 10 columns (correct). Path B (NOTIFY handler) writes 8 columns (stale) and overwrites Path A within minutes.
5. **Diagnose:** Trace Path B's connection. It reuses a pooled connection whose `information_schema` cache predates the migration. Every admin edit triggers Path B, which overwrites Path A's correct cache with stale data.

## Solution

**Immediate fix (5 minutes):** Restart the Notification Service. This creates fresh connections that know about the new columns. Both Path A and Path B will now write correct data.

**But this doesn't prevent recurrence on the next migration.**

**Proper fix (30 minutes):**

1. Remove Path B (the NOTIFY-triggered cache refresh). It's an optimization that causes more harm than good. The 1-hour TTL is sufficient for schema changes, which happen rarely.

2. If fast schema refresh is needed, replace Path B with an explicit cache invalidation: the migration script deletes the `schema:notifications` Redis key after running. The next read triggers a fresh cache fill from a new connection.

3. Add a startup check: on boot, the service compares its cached schema against a fresh `information_schema` query. Log a warning if they differ.

**Monitoring:**
- Log the column count every time the schema cache is refreshed, with the source (TTL vs NOTIFY)
- Alert if a notification is sent without applying all configured rules (priority, throttling)
- Add an integration test that adds a column and verifies the Notification Service picks it up within 2 TTL cycles

## Blast Radius

- **All notifications sent during the 48-hour window** were unthrottled and unfiltered by priority. If "critical only" was configured, low-priority notifications were also sent — potential user annoyance or compliance issues.
- **Notification volume:** Without throttling, burst notifications may have triggered rate limits at email/SMS providers, causing legitimate critical notifications to be delayed or dropped.
- **Other tables using the same dynamic schema cache:** If any other table was migrated, the same stale-cache pattern applies. Audit all `schema:*` keys in Redis.
- **Connection pool age:** Other services using SQLAlchemy with long-lived connection pools may have similar stale-metadata issues. This isn't specific to schema caching — any `information_schema` query on a pre-migration connection returns old data.

## Lessons

- Dynamic schema mapping is powerful but creates an invisible dependency on cache freshness. When the cache is stale, the system doesn't fail — it silently degrades. This is worse than failing because no one notices.
- Two cache refresh paths with different data sources are a P02 (multiple writers) waiting to happen. The more-frequent writer wins, regardless of correctness.
- "No errors in logs" is not the same as "working correctly." Features that degrade silently need positive confirmation ("applied priority filter: critical") not just absence of errors.
- Connection pools carry invisible state. A connection opened before a migration has a different view of the database schema than one opened after. Restarting the service fixes it, but the next migration will break it again unless the pool is explicitly refreshed.
