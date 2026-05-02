---
id: P22
name: Iterative Fix Regression (Failswitch)
category: llm-ai
severity: high
frequency: common
---

# P22: Iterative Fix Regression (Failswitch)

## Pattern

A bug is "fixed" iteratively — each attempt addresses the observed symptom but not the structural root cause. After the 2nd failed fix, the system is now harder to debug because the original signal is buried under compensating logic (guards, retries, error messages). The fix attempts themselves become part of the problem: they mask symptoms, add code paths, and shift behavior in ways that make the real root cause invisible. This is especially common with LLM-integrated systems where the model's behavior is non-deterministic and ignoring tool results is indistinguishable from "result not delivered."

## Check List (30-Second Diagnosis)

- [ ] Has the same symptom been "fixed" 2+ times with different code changes?
- [ ] Does the current codebase contain guard/retry/kill logic added specifically for this bug?
- [ ] Is the original error still reproducible despite the accumulated fixes?

If 2+ checks are "yes," this pattern likely matches.

## Examples

### Example 1: Gemini Live Infinite Tool Call Loop
**Setup:** Voice pipeline uses Gemini Live S2S. `check_availability` tool returns empty slots (no DMS data), Gemini calls it 12+ times per call creating 60s dead-air gaps. Real customers affected (465s call).
**Symptom:** Caller hears silence for 30-60 seconds, says "Hallo? Hallo?" — agent doesn't respond.
**Fix attempt 1:** Added per-date loop guard with error text in `result_callback` — Gemini ignores it.
**Fix attempt 2:** Circuit breaker returning structured `{"available": true, "noted": true}` via `result_callback` — Gemini still ignores it. Data analysis confirmed circuit breaker fired 8+ times, all results dropped.
**Fix attempt 3:** Increased dedup window, returned positive structured data — still 12 calls in one session.
**Root cause (found after deep multi-agent analysis):** `result_callback()` broadcasts a `FunctionCallResultFrame` into the pipeline, but S2S mode has NO context aggregator — the frame goes to transport (ignored). **Tool results never reached Gemini at all.** The flow manager uses `_tool_result()` to send directly via WebSocket, but handlers registered via `register_function()` bypassed this path. Two delivery mechanisms existed — one worked, one silently dropped results with no error.
**Fix:** Added `_send_tool_result()` helper that calls `gemini_live._tool_result()` directly, matching the flow manager's working path.

### Example 2: Retry Storm in API Integration
**Setup:** Webhook handler retries on 5xx errors with exponential backoff. Target API returns 503 during maintenance.
**Symptom:** Queue backs up, processing latency spikes from seconds to hours.
**Fix attempt 1:** Reduced max retries from 10 to 3 — queue still backs up, just slower.
**Fix attempt 2:** Added circuit breaker that stops retries after 5 consecutive failures — but circuit breaker resets on any success, and one healthy endpoint keeps it open for all routes.
**Root cause:** The retry mechanism was per-request, but the failure was per-service. Individual request retries can never solve a service-level outage. Needed a service-level health check that pauses ALL requests to a down service.
**Fix:** Service-level circuit breaker (not per-request), health check endpoint, dead-letter queue for failed messages during outage.

## Fix Strategy

1. **STOP iterating.** If the same symptom persists after 2 fix attempts, do NOT try a 3rd variation of the same approach.
2. **Inventory the accumulated fix logic.** List every guard, retry, kill switch, error handler added for this bug. Understand what each one actually does vs. what it was supposed to do.
3. **Trace the FULL path.** Don't start from your fix — start from the original trigger (user action, API call, frame event) and follow every step to the symptom. The root cause is usually upstream of where you've been looking.
4. **Research externally.** Check if the behavior is a known platform bug (GitHub issues, forums, docs). Your assumption about how the platform works may be wrong.
5. **Fix the structural cause.** The fix should make the compensating logic unnecessary, not add more of it. If your fix requires keeping the old guards, you haven't found the root cause.
6. **Remove dead fix logic.** Clean up guards/retries that are now unnecessary. They add complexity and will confuse future debuggers.

## Prevention

- **Enforce the 3-exchange rule:** After 2 failed fix attempts, mandatory deep analysis before attempt 3. No exceptions.
- **Distinguish "model ignores X" from "X never reaches model":** In LLM systems, instrument the delivery path before assuming the model is misbehaving. Log what actually gets sent over the wire.
- **Use structured data, not text instructions, for tool results:** LLMs (especially multimodal/live) respond to data structure (booleans, enums) more reliably than natural language instructions in tool responses.
- **Test the "no data" path explicitly:** When a function has a "data not available" branch, ensure it returns a DISTINGUISHABLE result from "negative result." Empty list means different things in different contexts.

## Debugger Strategy

When an agent has access to a runtime debugger (PDB, JDB, or equivalent), use these targeted investigation steps instead of blind stepping.

**Breakpoints:**
- The DELIVERY point of the tool result — for Gemini Live S2S this is `gemini_live._tool_result()` or `_send_tool_result()`; for standard LLMs it's wherever `FunctionCallResultFrame` is enqueued — NOT where the result is generated
- `result_callback()` — Break here and inspect whether the frame it produces is routed to a context aggregator or directly to transport (the silent-drop point)

**Watch Expressions:**
- `websocket.send()` payload — Confirm the tool result JSON actually goes over the wire; absence here is definitive proof of silent drop
- `context_aggregator.messages` after `result_callback()` — If the tool result does not appear here, it was never aggregated and the model never saw it
- `circuit_breaker.trip_count` or `guard.invocation_count` — A high value (8+) while the symptom persists proves the guard fires but has no effect

**Isolation Technique:**
Break at the delivery point and manually inspect the WebSocket send buffer or context aggregator state. If the tool result is absent from both, the delivery path is broken — everything upstream (generation, guards, retries) is irrelevant.

**Expected Evidence:**
Confirms pattern: tool result generated correctly, `result_callback()` called, but `websocket.send()` never carries the result payload and `context_aggregator.messages` never includes it. Rules it out: result appears in the WebSocket send buffer — delivery is working, the model is genuinely ignoring it.

## Related Patterns

- **P18** — Model Loops Without Stop Signal: the specific loop behavior that often triggers iterative fix regression
- **P19** — Prompt Engineering Has Hard Limits: when text-based fixes fail because the problem is structural, not linguistic
- **P21** — Untested Handler Path: the "no data" code path that returns ambiguous results
