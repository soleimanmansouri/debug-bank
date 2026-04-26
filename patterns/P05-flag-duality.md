---
id: P05
name: Context-Dependent Flag Duality
category: code-structure
severity: medium
frequency: occasional
---

# P05: Context-Dependent Flag Duality

## Pattern

A framework flag or configuration parameter needs different values in different contexts, but is set globally. One context works correctly; the other silently breaks.

## Check List (30-Second Diagnosis)

- [ ] Is a flag/parameter set globally (or as a default)?
- [ ] Does the bug appear only in specific contexts (certain pages, routes, modes)?
- [ ] Does the bug disappear when you flip the flag — but then a different context breaks?

If 2+ checks are "yes," this pattern likely matches.

## Examples

### Example 1: Immediate Response Flag
**Setup:** A pipeline has `auto_respond=False` globally. Entry nodes after routing need `=True` to avoid dead air.
**Symptom:** After routing to a new flow, the agent is silent for 3-5 seconds.
**Root cause:** Global `False` is correct for most nodes, but entry nodes need `True`.
**Fix:** Set per-node: `auto_respond=True` only on entry nodes.

### Example 2: Caching Flag
**Setup:** `cache_enabled=True` globally. API endpoints need caching, but webhook handlers process unique events.
**Symptom:** Webhook events are "lost" — the handler returns cached responses for duplicate-looking payloads.
**Root cause:** Webhook handler inherits global caching, but every webhook payload is unique.
**Fix:** Set `cache_enabled=False` on webhook route handlers.

## Fix Strategy

1. Identify which contexts need which value
2. Move the flag from global to per-context (per-route, per-node, per-handler)
3. Verify BOTH contexts work with their respective values

## Prevention

- When setting global flags, ask: "Does every context need this value?"
- Document which contexts override the global default
- Test edge contexts (entry points, exit points, error paths) explicitly

## Related Patterns

- **P07** — Stale config can mask the real value a context is using
- **P10** — Contradictory config is a multi-source version of this pattern
