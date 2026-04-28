# Difficulty Tiers — Scaling the Debug Trajectory Protocol

The 7-step protocol is the same at every tier, but the rigor, tooling, and time investment scale with the bug's scope. Use this guide to right-size your investigation.

## Tier Definitions

### L1: Single-File Bug

**Scope:** The root cause and symptom are in the same file.

**Examples:** Off-by-one error, wrong variable name, missing null check, incorrect regex.

**Protocol Adjustments:**
- **Pattern Check:** Scan titles only — L1 bugs rarely match production patterns
- **Reproduce:** Run the function/test directly
- **Hypothesize:** 1-2 hypotheses are sufficient
- **Isolate:** Read the function, add a print statement
- **Diagnose:** Usually obvious once reproduced
- **Record:** Only record if it reveals a new pattern. Most L1 bugs are one-offs.

**Time budget:** 5-30 minutes.

**Typical patterns:** None (too simple for pattern matching). Occasionally P05 (flag duality) in a single config file.

---

### L2: Multi-File, Single Service

**Scope:** The symptom is in file A but the root cause is in file B within the same service/application.

**Examples:** A controller returns wrong data because a service layer function has a bug. A component renders incorrectly because a parent passes wrong props. A migration breaks because a model definition is inconsistent.

**Protocol Adjustments:**
- **Pattern Check:** Full check-list scan — L2 bugs often match P01, P04, P05, P07
- **Reproduce:** Run the service locally, trigger the endpoint/flow
- **Hypothesize:** 2-3 hypotheses, trace the call chain across files
- **Isolate:** Binary search by adding logging at layer boundaries (controller → service → repository)
- **Diagnose:** Trace the full call chain. Check for "root cause behind the root cause"
- **Record:** Record with the standard template. Link to pattern if matched.

**Time budget:** 30 minutes - 2 hours.

**Typical patterns:** P01 (wrapper defaults), P04 (LLM copies examples), P05 (flag duality), P07 (stale config), P09 (auto-apply corruption).

---

### L3: Multi-Service, Single Machine/Cluster

**Scope:** The symptom is in service A but the root cause is in service B (or the interaction between A and B). Both services run in the same environment.

**Examples:** Service A writes correct data but service B reads stale cache. An event published by service A is processed incorrectly by service B due to schema mismatch. A config change in the admin panel affects a background worker in unexpected ways.

**Protocol Adjustments:**
- **Pattern Check:** Full check-list scan + composition check (see `compositions/`). L3 bugs usually involve 2+ patterns.
- **Reproduce:** Requires running multiple services. Use Docker Compose or the staging environment.
- **Hypothesize:** 3 hypotheses minimum, spanning both services. At least one hypothesis should be "the bug is in the interaction, not in either service."
- **Isolate:** Test each service independently first. If both work alone, the bug is in the interaction — narrow to the integration boundary (API contract, shared database, message format).
- **Diagnose:** Trace the data flow across services. Log at every service boundary. Check for write races (P02), config chain gaps (P08), and schema drift.
- **Record:** Record with full trajectory. Always note which service the symptom appeared in vs. which service the root cause was in.

**Time budget:** 2-8 hours.

**Typical patterns:** P02 (multiple writers), P08 (config chain gap), P10 (contradictory config), P13 (silent success). Compositions: C01, C03.

**Key tool:** Distributed tracing (request IDs across services). Without it, add temporary correlation IDs to every cross-service call.

---

### L4: Distributed / Timing-Dependent

**Scope:** The bug depends on timing, ordering, concurrency, or network conditions. It may not be reproducible deterministically. The root cause might be a race condition, a retry cascade, a cache coherence issue, or a clock skew problem.

**Examples:** Cache invalidation race (read-through fills stale data after invalidation). Retry storm amplification across multiple layers. Eventual consistency violation where "eventually" is longer than the read timeout. Split-brain scenario where two services disagree on state.

**Protocol Adjustments:**
- **Pattern Check:** Full check-list + composition check + review of `scenarios/` for similar architecture. L4 bugs almost always involve pattern compositions.
- **Reproduce:** May require load testing, artificial latency injection, or chaos engineering tools. If you can't reproduce deterministically, reproduce statistically (run 1000 requests, observe the failure rate).
- **Hypothesize:** 3+ hypotheses. At least one must involve timing/ordering. Draw a timeline of events across services — sequence diagrams are not optional at L4.
- **Isolate:** Cannot use simple binary search. Instead: add timestamps to every operation across all services. Reconstruct the event timeline. Look for ordering violations (event A should happen before event B but doesn't always).
- **Diagnose:** The root cause is usually "two things that should be ordered aren't." Identify the ordering assumption that's violated. Check: Is there a distributed lock that should exist? Is there a version check that's missing? Is there a TTL that's too long/short?
- **Record:** Record with detailed timeline. Include the specific timing condition that triggers the bug (e.g., "fails when cache invalidation arrives between the cache miss and the read-through fill"). Note: "X% of the time under Y conditions" is acceptable — not all L4 bugs reproduce 100%.

**Time budget:** 4 hours - 2 days.

**Typical patterns:** P02 (multiple writers with timing), P06 (dependency cascade under load), P03 (retry multiplier). Compositions: C01, C02.

**Key tools:**
- Distributed tracing with timing (Jaeger, OpenTelemetry)
- Load testing with degraded dependencies (not just high traffic)
- Redis `MONITOR` or database `log_statement = 'all'` for operation ordering
- Sequence diagrams for the hypothesized vs. actual event order

---

## Tier Selection Guide

```
Is the bug in one file?
  → YES: L1
  → NO:
    Is the bug in one service?
      → YES: L2
      → NO:
        Is it reproducible deterministically?
          → YES: L3
          → NO: L4
```

**When to upgrade your tier assessment:**
- L1 fix doesn't resolve the bug → re-assess as L2
- L2 investigation traces the cause outside the service → upgrade to L3
- L3 investigation finds the bug is timing-dependent → upgrade to L4
- The 3-Exchange Rule fires → consider if you've underestimated the tier

**When to downgrade:**
- L4 investigation reveals the bug only appeared timing-dependent because of a simple config error → downgrade to L2/L3
- Don't over-invest in distributed tracing for what turns out to be a typo

## Protocol Constants Across All Tiers

These rules apply regardless of tier:

1. **3-Exchange Rule:** Always enforced. 3 failed hypotheses → STOP and re-plan.
2. **Pattern Check First:** Always the first step. Even for L1 bugs, a 30-second scan costs nothing.
3. **Record After Fix:** Always record the trajectory. The severity of the recording matches the tier — L1 gets a one-liner, L4 gets a full timeline.
4. **Root Cause, Not Symptom:** Never accept a symptomatic fix at any tier. The temptation increases with tier (L4 bugs are hard and "it seems to work now" is tempting). Resist.
