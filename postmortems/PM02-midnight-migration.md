---
id: PM02
name: Midnight Migration
date: 2025-09-22
duration: 2h 10m
severity: SEV-1
patterns: [P02, P08]
---

# PM02: Midnight Migration

## Summary

A scheduled database migration ran at 00:00 UTC while a nightly data sync job was writing to the same tables. The migration added a NOT NULL column with a default, which acquired an ACCESS EXCLUSIVE lock. The sync job held row-level locks for its transaction. The migration waited for the sync job; the sync job's subsequent queries waited for the migration. Deadlock. Both processes were killed after 45 minutes, resulting in 30 minutes of data loss from the interrupted sync job and a 2-hour full outage.

## Timeline

| Time (UTC) | Event |
|------------|-------|
| 23:45 | Nightly data sync job starts (runs ~23:45-00:30 daily) |
| 00:00 | CI/CD pipeline triggers scheduled migration: `ALTER TABLE orders ADD COLUMN region TEXT NOT NULL DEFAULT 'us-east'` |
| 00:00 | Migration acquires ACCESS EXCLUSIVE lock request on `orders` table — blocked by sync job's row locks |
| 00:00 | All subsequent queries against `orders` queue behind the migration's lock request |
| 00:01 | API response times spike from 50ms to 30s (queries queuing) |
| 00:02 | Health checks start failing (30s timeout exceeded) |
| 00:03 | Load balancer marks all API instances as unhealthy → full outage |
| 00:05 | PagerDuty alert fires: "All instances unhealthy" |
| 00:08 | On-call engineer connects, sees migration is "waiting for lock" |
| 00:12 | Engineer identifies sync job as the lock holder via `pg_locks` |
| 00:15 | Engineer hesitates — killing the sync job means losing 15 minutes of synced data |
| 00:30 | After 15 minutes of deliberation with team lead, decides to kill the sync job |
| 00:31 | Sync job killed. Migration acquires lock. But migration itself takes 12 minutes on the 50M-row table |
| 00:43 | Migration completes. Lock released. Queries start processing |
| 00:45 | API instances recover. Health checks pass |
| 01:00 | Sync job re-run manually. But the sync source's window has advanced — 30 minutes of data between 23:45-00:15 is no longer available in the source system's "recent changes" API |
| 01:30 | Data team begins manual reconciliation of the 30-minute gap |
| 02:10 | Reconciliation complete. All-clear confirmed |

## Detection

PagerDuty alert at 00:05 — 5 minutes after the migration started. Detection was fast because health checks have a 30-second timeout and the load balancer requires 3 consecutive failures (90 seconds) plus the PagerDuty routing adds ~2 minutes.

The alert was correct but generic: "All instances unhealthy." It didn't indicate WHY.

## Root Cause

**P02 (Multiple Writers) + P08 (Config Chain Gap)**

**P02 — Two writers on the same table at the same time:**
The sync job writes to `orders` in a long-running transaction (~45 minutes). The migration also needs exclusive access to `orders`. Neither system knew about the other's schedule. The sync job was scheduled by the data team in their cron. The migration was scheduled by the platform team in CI/CD. No shared calendar or lock coordination existed.

**P08 — Migration scheduling falls through a config gap:**
The CI/CD pipeline's migration schedule was configured to run "at 00:00 UTC during low-traffic window." This was set 18 months ago when no jobs ran at midnight. The data team added the sync job 6 months ago, scheduled for 23:45. Neither team checked the other's schedule. The "low traffic" assumption was correct for user traffic but ignored background jobs.

The deadlock specifically: Postgres `ALTER TABLE ... ADD COLUMN NOT NULL DEFAULT` on a large table requires ACCESS EXCLUSIVE lock. This lock type conflicts with ALL other locks, including the ROW EXCLUSIVE locks held by the sync job's INSERT/UPDATE statements. The migration waits for existing locks to release. But critically, while the migration waits, it blocks ALL new queries against the table — even simple SELECTs. This is why the entire API went down, not just writes.

## False Leads

### False Lead 1: Database Running Out of Connections
- **Time spent:** 3 minutes
- **What was checked:** `SELECT count(*) FROM pg_stat_activity`
- **Why it was ruled out:** Connection count was 45/200 — not exhausted. Connections were active but waiting, not missing.
- **Lesson:** Quick to check and rule out. Good first hypothesis.

### False Lead 2: API Code Deadlock
- **Time spent:** 0 minutes
- **What was checked:** N/A — engineer went straight to `pg_locks` after ruling out connections
- **Lesson:** The engineer's instinct to check database locks was correct. Waiting queries + all instances affected = database-level issue.

## Resolution

1. Killed the sync job (`SELECT pg_terminate_backend(pid)`)
2. Waited 12 minutes for migration to complete on the 50M-row table
3. Re-ran sync job, discovered 30-minute data gap
4. Manual reconciliation from backup source

The 15-minute deliberation (00:15-00:30) about whether to kill the sync job extended the outage significantly. The team was weighing "lose 15 minutes of sync data" vs "continue full API outage." In hindsight, killing the job immediately was obviously correct — the API outage affected all users, the sync data gap affected one pipeline.

## Blast Radius

### Direct Impact
- Full API outage for all users: 00:02-00:45 (43 minutes)
- 30 minutes of sync data lost (23:45-00:15 window)
- Downstream systems that depend on the orders table received stale data during the outage

### Indirect Impact
- Webhook retries queued during the outage. When the API recovered, 43 minutes of retries hit simultaneously, causing a brief 2x load spike
- Customers who submitted orders during the outage received generic error pages. Three customers contacted support assuming their orders were lost (they were never submitted)

### Near Misses
- The migration was `NOT NULL DEFAULT` — if it had been `NOT NULL` without a default, Postgres would have needed to scan and validate every existing row, taking even longer
- A second migration was scheduled 5 minutes after the first (adding an index). If the first migration hadn't caused an outage, the second would have further extended the lock window

## What Went Well

- On-call engineer correctly diagnosed the lock contention within 7 minutes
- `pg_locks` query was ready in the team's runbook — no time spent figuring out how to check
- The sync job's data gap was identified immediately, not discovered days later

## What Went Poorly

- **15-minute deliberation** about killing the sync job doubled the outage duration. No pre-established decision framework for "API outage vs. data pipeline interruption" trade-offs
- **No migration safety check.** The CI/CD pipeline didn't verify that no long-running transactions were active before running the migration
- **No shared schedule.** Data team and platform team scheduled jobs independently on the same database without coordination
- **The migration wasn't tested on production-sized data.** Staging has 500K rows (completes in <1 second). Production has 50M rows (takes 12 minutes). The lock duration was unknown

## Systemic Mitigation

| Action | Prevents | Status |
|--------|----------|--------|
| Pre-migration check: abort if active transactions on target table exceed 60s | Lock contention with background jobs | Done |
| Shared job schedule in team wiki, reviewed before adding new jobs | Schedule collisions between teams | Done |
| Migration CI runs against production-size dataset (anonymized copy) to measure duration | Unknown lock duration on large tables | In progress |
| Decision framework: "If choice is between full outage and pipeline interruption, always resolve the outage first" | Deliberation delay during incidents | Done |
| Use `ALTER TABLE ... ADD COLUMN` without NOT NULL + backfill + add constraint pattern for large tables | ACCESS EXCLUSIVE lock on large tables | Done |

## Patterns

- **P02 (Multiple Writers):** The sync job and the migration both needed exclusive access to the `orders` table. Neither knew about the other. This is "multiple writers" at the lock level, not the data level.
- **P08 (Config Chain Gap):** The migration schedule was set based on "low traffic" analysis that only checked user traffic. Background job traffic was a gap in the analysis. The correct answer (run at 03:00 when the sync job is done) was available but never checked.
