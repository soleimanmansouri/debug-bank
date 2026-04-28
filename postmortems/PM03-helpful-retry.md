---
id: PM03
name: The Helpful Retry
date: 2026-01-08
duration: 35m
severity: SEV-1
patterns: [P06, P03]
---

# PM03: The Helpful Retry

## Summary

A library upgrade silently enabled automatic retries on HTTP POST requests. During a 10-minute payment gateway slowdown, retries amplified traffic 6x, causing duplicate payments. 312 customers were charged twice, totaling $23,400 in erroneous charges. Resolved in 35 minutes once detected, but financial reconciliation took 3 days.

## Timeline

| Time (UTC) | Event |
|------------|-------|
| 14:00 | Sprint deployment includes `http-client` library upgrade 3.2→3.4 (among 12 dependency updates) |
| 14:00 | New default: `retry_on_timeout=True, max_retries=2` (previously: no retries) |
| 16:30 | Payment gateway begins scheduled maintenance, response time increases from 200ms to 4s |
| 16:30 | Timeout threshold (3s) exceeded → retries kick in |
| 16:31 | Payment service traffic to gateway: 100 req/s → 300 req/s (each request retried 2x) |
| 16:32 | Gateway slows further under 3x load → more timeouts → more retries |
| 16:33 | Effective traffic: ~600 req/s (retry cascade) |
| 16:35 | Gateway processes retried requests as new requests → duplicate charges begin |
| 16:40 | Customer support receives first "charged twice" complaint |
| 16:42 | Support escalates to engineering |
| 16:45 | Engineer checks payment logs — sees duplicate transaction IDs from the application side but different transaction IDs on the gateway side |
| 16:50 | Engineer finds retry config in `http-client` 3.4 changelog |
| 16:55 | Disables retries via config override: `HTTP_CLIENT_RETRY_ENABLED=false` |
| 16:55 | Traffic to gateway drops immediately to normal |
| 17:05 | All-clear confirmed. Duplicate charge audit begins |
| 17:05+3d | Financial reconciliation: 312 customers refunded |

## Detection

Customer complaint at 16:40 — 10 minutes after duplicates started. No automated detection because:

1. Payment success rate was 100% (retries succeeded — that was the problem)
2. Transaction volume increase matched "expected variance" thresholds (3x wasn't enough to trigger the anomaly detector, which expected flash-sale spikes)
3. No duplicate-payment alert existed (unique constraint was on the gateway's transaction ID, not the application's)

## Root Cause

**P06 (Dependency Resolution Cascade) + P03 (Observer/Hook Multiplier)**

**P06:** The `http-client` library upgrade from 3.2 to 3.4 changed the default retry behavior. Version 3.2 had no automatic retries. Version 3.4 introduced "resilient defaults" — `retry_on_timeout=True` with `max_retries=2`. The changelog mentioned "improved timeout handling" without explicitly stating that POST requests would now be retried.

The team reviewed the changelog but focused on the security patches (the reason for the upgrade). The retry default change was listed under "Improvements" without a migration warning.

**P03:** The retry mechanism multiplied every request. At 2 retries per timeout, a single slow period turned 100 req/s into 300 req/s. The additional load made the gateway slower, causing more timeouts, causing more retries. Peak amplification reached 6x before the retries were disabled.

The payment gateway treated each HTTP request as an independent transaction. The application included an `X-Idempotency-Key` header, but the gateway only enforced idempotency within a 60-second window. Retries that arrived more than 60 seconds after the original (due to gateway slowness + retry backoff) were processed as new charges.

## False Leads

### False Lead 1: Payment Gateway Bug
- **Time spent:** 3 minutes
- **What was checked:** Gateway status page, recent gateway changelog
- **Why it was ruled out:** Gateway was slow (maintenance) but functioning correctly. It processed what it received. The problem was what was being sent.
- **Lesson:** "Gateway is slow" and "customers are charged twice" are two separate symptoms. The investigation should have checked for a connection between them immediately.

## Resolution

Environment variable override to disable retries:

```bash
HTTP_CLIENT_RETRY_ENABLED=false
```

Applied via config management, propagated to all instances within 60 seconds.

Followed by pinning the retry config in the application's initialization:

```python
http_client.configure(retry_on_timeout=False, max_retries=0)
```

## Blast Radius

### Direct Impact
- 312 customers charged twice ($23,400 total)
- Payment gateway received 6x normal traffic for 25 minutes, delaying other merchants' transactions
- Customer trust impacted — "you charged me twice" is one of the highest-severity customer complaints

### Indirect Impact
- Accounting reconciliation: 3 days of manual work to identify and reverse duplicates
- Payment gateway flagged the merchant account for "unusual activity" — required a call to prevent account suspension
- Monthly fraud metrics skewed by the duplicate transactions — required annotation in reports for the next quarter

### Near Misses
- The same `http-client` library is used by the email notification service. If the email gateway had been slow, customers would have received duplicate emails. It wasn't slow this time.
- The application's subscription renewal endpoint also uses `http-client`. If renewals had timed out, customers would have been renewed twice. Renewal didn't run during the incident window.

## What Went Well

- Once the engineer found the retry config (16:50), disabling it took only 5 minutes. The environment variable override pattern allowed a fix without redeployment.
- Customer support escalated quickly (2 minutes from complaint to engineering)
- The payment system's internal logs included enough detail to identify exactly which transactions were duplicates

## What Went Poorly

- **No review of default changes in dependency upgrades.** The team reviewed the changelog for security fixes but skimmed the "Improvements" section. Default behavior changes are the most dangerous part of any upgrade.
- **No idempotency at the application level.** The application relied on the gateway's idempotency window (60s), which was insufficient for retried requests with backoff.
- **No anomaly detection on duplicate payments.** A simple check — "same customer, same amount, within 5 minutes" — would have caught this in seconds.
- **Retry behavior was not tested.** Integration tests mocked the HTTP client, so the retry behavior was never exercised in tests.

## Systemic Mitigation

| Action | Prevents | Status |
|--------|----------|--------|
| Pin ALL HTTP client config explicitly — no reliance on library defaults | Silent behavior changes from upgrades | Done |
| Add `same customer + same amount + 5min window` duplicate detection alert | Duplicate payment detection | Done |
| Application-level idempotency: generate and persist idempotency key before sending, enforce at application layer | Duplicate charges regardless of gateway idempotency | Done |
| Dependency upgrade checklist: diff all default values, not just API changes | P06 pattern across all libraries | Done |
| Integration tests with real HTTP calls (no mocking) for payment paths | Retry and timeout behavior coverage | In progress |

## Patterns

- **P06 (Dependency Resolution Cascade):** The library upgrade changed default retry behavior from "never retry" to "retry twice on timeout." This is the canonical form of P06 — a dependency update changes internal behavior without changing the API surface.
- **P03 (Observer/Hook Multiplier):** Each retry is effectively a hook that fires on timeout. With 2 retries × cascading slowness, one request becomes 3-6 downstream calls. The multiplier effect is the same whether it's an event hook firing multiple times or a retry mechanism re-sending requests.
