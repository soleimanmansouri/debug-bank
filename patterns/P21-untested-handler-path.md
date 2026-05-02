---
id: P21
name: Untested Handler Path After Shared Code Change
category: code-structure
severity: high
frequency: common
---

# P21: Untested Handler Path After Shared Code Change

## Pattern

A change to shared code (utility function, decorator, base class method, or pipeline middleware) is tested through one handler path but not others. Handler A (e.g., reschedule) works fine because its lifecycle is simple. Handler B (e.g., transfer) breaks because it has a unique teardown sequence (CancelFrame + transport dial + EndFrame) that interacts differently with the change. The assumption that all handlers behave uniformly causes regressions in untested paths.

## Check List (30-Second Diagnosis)

- [ ] Was shared code (used by multiple handlers) recently modified?
- [ ] Was the change tested through only one handler path?
- [ ] Do the affected handlers have different lifecycle requirements (different teardown, different frame sequences, different transport operations)?

If 2+ checks are "yes," this pattern likely matches.

## Examples

### Example 1: Filler Added to All Handlers, Only Reschedule Tested
**Setup:** A filler audio feature is added to a shared handler decorator. The developer tests with the reschedule flow (which ends with a simple TTS response). The transfer flow (which ends with CancelFrame + Twilio dial + EndFrame) is not tested.
**Symptom:** Reschedule calls work perfectly. Transfer calls hang — the agent says "transferring" but the transfer never completes.
**Root cause:** The filler decorator wraps the entire handler including teardown. Reschedule has no control frames in teardown, so it works. Transfer's CancelFrame is blocked by filler frames (P20).
**Fix:** Test every handler path individually. Discovered that filler must stop before control frames, which only matters for the transfer path.

### Example 2: Timeout Change Breaks One Endpoint
**Setup:** A shared HTTP client timeout is increased from 5s to 30s. The change is tested with the search endpoint (which benefits from longer timeout). The health-check endpoint (which has a 10s SLA) is not tested.
**Symptom:** Health-check monitoring triggers false alarms because slow upstream responses are now waited on for 30s instead of failing fast at 5s.
**Root cause:** Health-check needs fast failure, not patience. The uniform timeout change violated its implicit contract.
**Fix:** Per-endpoint timeout overrides for handlers with different timing requirements.

## Fix Strategy

1. Identify ALL handlers/consumers of the changed shared code
2. Categorize handlers by lifecycle type (simple response, multi-step, teardown with control frames, transport operations)
3. Test at least one handler from each lifecycle category
4. Pay special attention to handlers with unique teardown or cleanup sequences

## Prevention

- Before deploying shared code changes, list every handler that uses the changed code
- Create a handler matrix: for each handler, document its lifecycle type and unique requirements
- Test the handler with the most complex lifecycle FIRST — if that works, simpler ones likely work too
- In CI, tag handlers by lifecycle type and require at least one test per type when shared code changes
- Pre-deploy checklist: "Which handlers use this code? Which have unique lifecycles? Did I test those?"

## Debugger Strategy

When an agent has access to a runtime debugger (PDB, JDB, or equivalent), use these targeted investigation steps instead of blind stepping.

**Breakpoints:**
- Entry point of the shared function or decorator (e.g., `handler_decorator.__call__()`) — Set once; note the full call stack on each hit to distinguish Handler A vs Handler B invocations
- The divergence branch inside the shared code (any `if`/`elif` that checks handler type or lifecycle state) — This is where Handler B takes a different path

**Watch Expressions:**
- `handler.__class__.__name__` or `handler.handler_type` — Identifies which handler is executing the shared code
- `teardown_sequence` or `frame_sequence` list — Comparing Handler A's sequence to Handler B's sequence at the same breakpoint reveals the lifecycle difference
- `filler.is_active` at the point of `queue_frame(CancelFrame)` — The classic divergence for the filler/transfer case

**Isolation Technique:**
Run Handler A to completion while recording every branch taken in the shared code. Then run Handler B. Step through the same shared code and watch for the first branch where execution diverges. That branch is the untested path.

**Expected Evidence:**
Confirms pattern: Handler A and Handler B hit a different branch in the shared code; Handler B's branch was never exercised during the original test. Rules it out: both handlers follow identical execution paths through the shared code.

## Related Patterns

- **P20** — Filler pipeline contention is often discovered through this pattern (tested one handler, missed another)
- **P05** — Flag duality — different handlers may need different values for the same flag
- **P01** — Wrapper/decorator defaults that work for one consumer but not another
