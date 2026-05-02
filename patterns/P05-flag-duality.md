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

## Debugger Strategy

When an agent has access to a runtime debugger (PDB, JDB, or equivalent), use these targeted investigation steps instead of blind stepping.

**Breakpoints:**
- Flag read site in the working context (e.g., entry node `handle()` where `auto_respond` is checked) — Record flag value and current node/route identifier
- Flag read site in the broken context — Break at the same flag access in the silently-failing path

**Watch Expressions:**
- `self.auto_respond` — Should differ between entry nodes and regular nodes; if identical, the pattern is confirmed
- `current_node.node_type` or `request.path` — The context identifier that should determine which flag value applies
- `config.auto_respond` — The global setting; check if it is the only source, or if per-context overrides exist

**Isolation Technique:**
Break at the flag read in both contexts in the same debugging session. Compare the value and its source. If both read the same global value and one context needs a different value, the pattern is confirmed. Temporarily hardcode the correct value in the broken context and verify behavior improves — do not ship the hardcode, use it only to confirm the hypothesis.

**Expected Evidence:**
Confirms pattern: `auto_respond` is `False` in an entry node that is producing dead air, and no per-node override exists anywhere in the call path. Rules it out: the broken context has its own flag assignment that overrides the global — points to a logic bug instead.

## Related Patterns

- **P07** — Stale config can mask the real value a context is using
- **P10** — Contradictory config is a multi-source version of this pattern
