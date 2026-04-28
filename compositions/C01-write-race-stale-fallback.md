---
id: C01
name: Write Race + Stale Fallback
patterns: [P02, P08]
frequency: very-common
severity: high
---

# C01: Write Race + Stale Fallback

## The Composition

**P02 (Multiple Writers)** provides the mechanism: two code paths write to the same target.
**P08 (Config Chain Gap)** provides the data: one writer reads from a stale or wrong source in the fallback chain.

Alone, P02 causes data corruption when two valid writers conflict. Alone, P08 causes incorrect fallback values. Together, they create a system where a stale writer periodically overwrites a correct writer — and the bug self-heals and re-breaks on a timer, making it extremely hard to diagnose.

## Combined Check List

- [ ] Is the data intermittently correct and then incorrect again? (P02 timing)
- [ ] Does the correct/incorrect cycle correlate with a cache TTL or scheduled job? (P08 refresh)
- [ ] Are there 2+ code paths that write to the affected target? (P02)
- [ ] Does at least one writer read from a source that could be stale? (P08)
- [ ] Does the bug self-heal temporarily after a restart or cache clear? (both)

If 3+ are "yes," this composition likely matches.

## Why They Amplify

With P02 alone, you'd notice both writers and pick the correct one. With P08 alone, you'd fix the fallback chain. But combined:

1. You fix P08 (ensure correct source is populated) → bug persists because P02 writer overwrites it
2. You fix P02 (remove one writer) → bug persists because the remaining writer reads from P08's stale source
3. Only fixing BOTH simultaneously resolves the bug

## Signature Symptoms

- "It works for a while then breaks again" — the correct writer fills the cache (TTL), the stale writer overwrites it (on next event)
- "Restarting fixes it temporarily" — fresh connections/caches get correct data, but the stale writer re-triggers
- "The data in the database is correct" — the source of truth is fine; the bug is in the cache layer between two competing writers

## Real-World Example

**Scenario:** Notification service caches table schema in Redis. Two refresh paths: TTL-based (hourly, reads from new DB connections) and event-based (on every change, reuses pooled connections from before a migration). The event-based path runs more frequently and overwrites the TTL path's correct data with stale schema.

**How it was found:** Monitored Redis WRITE operations on the schema key. Observed two sources writing different column counts. The more-frequent writer was wrong.

**Fix:** Removed the event-based cache refresh (P02 fix) AND ensured the remaining path always uses a fresh connection (P08 fix).

## Investigation Strategy

1. **Identify all writers** to the affected target (grep, log, monitor)
2. **Trace each writer's data source** — where does it read from?
3. **Compare outputs** — do the writers produce the same data? If not, which is stale and why?
4. **Fix both:** Reduce to one writer AND ensure that writer reads from the authoritative source

## Related Compositions

- **C03 (P13 + P07):** Often appears alongside C01 — the stale writer's incorrect data doesn't trigger errors because P13 (silent success) hides the failure
