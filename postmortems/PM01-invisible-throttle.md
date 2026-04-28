---
id: PM01
name: The Invisible Throttle
date: 2025-11-14
duration: 4h 30m
severity: SEV-2
patterns: [P07, P13]
---

# PM01: The Invisible Throttle

## Summary

A rate-limiting configuration change intended for a single tenant was applied globally due to a config resolution fallback. 12% of API requests were silently throttled for 4.5 hours. No errors appeared in monitoring because throttled requests returned valid (but incomplete) responses. Discovered by a customer who noticed missing data in their dashboard.

## Timeline

| Time (UTC) | Event |
|------------|-------|
| 09:15 | Engineer applies rate limit override for tenant T-4821 via admin panel |
| 09:15 | Config service writes override to tenant-specific config in database |
| 09:16 | Config service ALSO writes to global fallback config (bug — see root cause) |
| 09:16 | All API instances pick up new global config within 30 seconds |
| 09:20 | ~12% of requests across all tenants begin hitting the new rate limit |
| 09:20 | Throttled requests return HTTP 200 with `"partial": true` in response body |
| 11:45 | Customer T-1093 opens support ticket: "Dashboard showing only ~88% of expected data since this morning" |
| 12:00 | Support escalates to engineering. Initial hypothesis: database query issue |
| 12:30 | Engineer checks database — data is complete. Hypothesis disproved |
| 12:45 | Engineer checks API response format — notices `"partial": true` flag on some responses |
| 13:00 | Engineer greps for what sets `partial: true` — finds the rate limiter |
| 13:10 | Rate limiter config checked — global rate limit is set to 50 req/min (should be 500) |
| 13:15 | Engineer traces the config change — finds it was written at 09:16, correlates with T-4821 override |
| 13:20 | Global rate limit reverted to 500 req/min |
| 13:25 | Throttling stops. API returns full responses |
| 13:45 | All-clear confirmed after monitoring shows 0% partial responses for 20 minutes |

## Detection

Discovered by a customer support ticket 2.5 hours after the incident began. No automated alert fired because:

1. HTTP status codes were all 200 (rate-limited responses returned 200 with partial data, not 429)
2. Error rate monitoring showed 0% errors (correct — there were no errors)
3. Response latency was normal (partial responses are faster than full responses)
4. Throughput was normal (requests weren't dropped, just given less data)

The `"partial": true` flag existed in the response schema but no monitoring checked for it.

## Root Cause

**P07 (Stale/Dead Config) + P13 (Parse Matches Errors as Success)**

The config service has a two-level resolution: tenant-specific → global fallback. When writing a tenant override, the admin panel calls:

```python
config_service.set_tenant_config(tenant_id, "rate_limit", 50)
```

This function writes to the tenant config table. But it also calls an internal `_ensure_fallback_exists()` method that checks if a global fallback exists for this key. If no global fallback exists, it creates one with the same value — the intent being "make sure there's always a default."

The global fallback for `rate_limit` already existed (value: 500). But `_ensure_fallback_exists()` used an UPSERT — `INSERT ... ON CONFLICT DO UPDATE`. It didn't check if the fallback already existed; it blindly overwrote it. So the tenant-specific value of 50 was also written as the global fallback.

Every API instance resolves: tenant config → global fallback. Tenants without their own override (88% of tenants) fell through to the global fallback, which was now 50 instead of 500.

The rate limiter returns partial data instead of 429 errors — a "graceful degradation" design that, in this case, made the failure invisible to monitoring.

## False Leads

### False Lead 1: Database Query Performance
- **Time spent:** 30 minutes
- **What was checked:** Slow query logs, database CPU, connection pool utilization
- **Why it was ruled out:** All database metrics were normal. Query plans hadn't changed.
- **Lesson:** The customer said "missing data," which anchored the investigation on the data layer. Should have checked the API response first.

### False Lead 2: CDN Cache Serving Stale Data
- **Time spent:** 15 minutes
- **What was checked:** CDN cache hit ratios, cache purge logs
- **Why it was ruled out:** CDN was returning fresh responses (verified by Cache-Status headers). The data was partial at the origin, not the CDN.
- **Lesson:** Ruled out quickly by checking response headers. Good hypothesis testing.

## Resolution

Reverted the global rate limit from 50 to 500 via direct database UPDATE:

```sql
UPDATE global_config SET value = '500' WHERE key = 'rate_limit';
```

Config service picked up the change within 30 seconds. Throttling stopped immediately.

## Blast Radius

### Direct Impact
- 12% of API requests across all tenants returned partial data for 4.5 hours
- Affected any tenant without a tenant-specific rate limit override (88% of tenants)
- Customer dashboards showed incomplete data, analytics were underreported

### Indirect Impact
- Three customers ran automated reports during the incident window. Reports were saved with incomplete data and needed to be regenerated.
- One customer's billing integration used the API data to calculate invoices. Two invoices were sent with incorrect (lower) amounts.

### Near Misses
- The `_ensure_fallback_exists()` method is also called for other config keys (feature flags, API version, timeout values). If the engineer had changed a timeout or feature flag for T-4821, those would also have been globally overwritten. Only rate_limit was changed today.

## What Went Well

- The `"partial": true` flag DID exist in responses — it just wasn't monitored. Once an engineer looked at the response body, the path to root cause was clear.
- The config service's 30-second polling meant the fix propagated quickly once applied.
- No data was lost — the underlying data was complete; only the API responses were truncated.

## What Went Poorly

- **Graceful degradation hid the failure.** Returning 200 with partial data instead of 429 meant no monitoring caught it. "Graceful" degradation that's invisible to operators is worse than a loud failure.
- **2.5-hour detection gap.** A customer found the issue, not monitoring. If no customer had checked their dashboard, this could have run for the full 1-hour config cache TTL × multiple cycles.
- **The `_ensure_fallback_exists()` UPSERT was written 2 years ago** and never reviewed. The original intent (ensure a default exists) was correct, but the implementation (overwrite unconditionally) was wrong.
- **No integration test** covered the scenario of "write tenant config, verify global config unchanged."

## Systemic Mitigation

| Action | Prevents | Status |
|--------|----------|--------|
| Add monitoring for `partial: true` response ratio exceeding 1% | Silent throttle incidents | Done |
| Change `_ensure_fallback_exists()` to INSERT-only (no UPDATE) | Global config overwrite from tenant changes | Done |
| Add audit log for all global config changes with diff | Unintentional global changes | Done |
| Review all "graceful degradation" paths — each must have a corresponding monitoring check | Invisible degradation across the platform | In progress |
| Add integration test: write tenant config → assert global config unchanged | Regression of this specific bug | Done |

## Patterns

- **P07 (Stale/Dead Config):** The global config became "stale" — not because it wasn't updated, but because it was overwritten with the wrong value. The runtime correctly read from the global fallback; the fallback was wrong.
- **P13 (Parse Matches Errors as Success):** The rate limiter's "graceful" 200 response with partial data was indistinguishable from success to all monitoring systems. The partial flag was present but unchecked.
