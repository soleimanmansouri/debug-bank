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
**Setup:** Voice pipeline uses Gemini Live S2S. `check_availability` tool returns empty slots (no DMS data), Gemini calls it 14+ times per call creating 60s dead-air gaps.
**Symptom:** Caller hears silence for 30-60 seconds, says "Hallo? Hallo?" — agent doesn't respond.
**Fix attempt 1:** Added per-date loop guard with counter — Gemini ignores the error message in `result_callback` and keeps calling.
**Fix attempt 2:** Added HARD KILL with stronger error text — Gemini still ignores all tool result content completely.
**Fix attempt 3:** Added `_avail_loop_count` global tracker — didn't help because Gemini switches to new dates, resetting per-date guards.
**Root cause (found after deep analysis):** Three layers: (1) `check_availability` returned `available_slots: []` for "no DMS data" — identical to "fully booked" — so handler told Gemini "no slots available" which triggered retry with new date. (2) Pipecat's 150ms dedup skipped execution but sent NO tool response — Gemini hangs without a response and retries. (3) All "fix" attempts used text instructions in `result_callback` — but Gemini Live ignores tool result TEXT content and only responds to structured data with positive signals.
**Fix:** (a) Return `{"available": true, "noted": true}` instead of empty slots when no DMS data exists. (b) Increase dedup to 3s and always send tool response. (c) Add total-calls circuit breaker (max 3) that returns positive result.

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

## Related Patterns

- **P18** — Model Loops Without Stop Signal: the specific loop behavior that often triggers iterative fix regression
- **P19** — Prompt Engineering Has Hard Limits: when text-based fixes fail because the problem is structural, not linguistic
- **P21** — Untested Handler Path: the "no data" code path that returns ambiguous results
