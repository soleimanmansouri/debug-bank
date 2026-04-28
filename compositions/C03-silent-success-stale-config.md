---
id: C03
name: Silent Success + Stale Config
patterns: [P13, P07]
frequency: common
severity: high
---

# C03: Silent Success + Stale Config

## The Composition

**P07 (Stale/Dead Config)** provides the incorrect data: the runtime reads from a config source that doesn't reflect reality.
**P13 (Parse Matches Errors as Success)** hides the failure: the system processes the stale config without errors, producing wrong results that look correct.

Alone, P07 would eventually surface when someone notices wrong values. Alone, P13 would be caught when error monitoring catches the misparse. Together, they create a silent failure that can persist for days or weeks — the system is confidently wrong, with 100% success rate and zero errors.

## Combined Check List

- [ ] Is the system producing wrong results with no errors? (P13)
- [ ] Does monitoring show 100% success / 0% errors? (P13)
- [ ] Is the system reading from a config source that could be outdated? (P07)
- [ ] Does restarting the service temporarily fix the issue? (P07 — fresh config load)
- [ ] Was a config migration, provider switch, or schema change made recently? (P07 trigger)

If 3+ are "yes," this composition likely matches.

## Why They Amplify

P07's stale config would normally be caught by downstream failures — wrong values cause errors. But P13's silent success swallows those errors:

1. Config says "use provider A" but the system was migrated to provider B (P07)
2. The system calls provider A, gets back an unexpected response format
3. The parser extracts data from the error response because the regex matches error text too (P13)
4. Result: wrong data, no errors, 100% "success" rate

## Signature Symptoms

- **"Everything looks green but customers say it's wrong"** — monitoring shows health, users report issues
- **Long detection time** — days or weeks before someone manually checks output quality
- **No error spike correlating with the config change** — the failure is invisible to standard monitoring
- **Works correctly after restart, breaks again later** — fresh config load vs. cached stale config

## Real-World Example

**Scenario:** Rate limiter uses a global config value that was silently overwritten from 500 to 50 req/min. Throttled requests return HTTP 200 with `"partial": true` instead of 429. Monitoring shows 0% errors and 100% success rate. Discovered by a customer 2.5 hours later.

**How it was found:** Customer reported incomplete dashboard data. Engineer checked API responses manually and noticed `"partial": true` flag that wasn't monitored.

**Fix:** Reverted config (P07 fix). Added monitoring for partial responses (P13 fix).

## Investigation Strategy

1. **Don't trust monitoring.** If users report wrong results but monitoring is green, the monitoring is wrong, not the users.
2. **Check output quality, not just output existence.** Fetch a real response and validate the content manually.
3. **Trace the full config chain** — where is the runtime actually reading from?
4. **Look for "graceful degradation" paths** — any code that returns 200 with partial/empty/default data instead of an error is a P13 candidate.

## Prevention

- Every "graceful degradation" code path must have a corresponding monitoring metric
- Config changes should emit audit events that are independently verified
- Add "output quality" checks alongside "output success" checks — synthetic monitoring that validates content, not just HTTP status

## Related Compositions

- **C01 (P02 + P08):** Often the stale config in C03 was overwritten by a second writer (C01). The three-pattern combo P02+P07+P13 is the hardest form to diagnose.
