---
id: P18
name: Model Loops Without Stop Signal
category: llm-ai
severity: high
frequency: occasional
---

# P18: Model Loops Without Stop Signal

## Pattern

A voice or streaming LLM generates output in a loop (repeating farewells, filler phrases, acknowledgments) when there's no explicit stop signal from the pipeline. Generous timeouts and debounce settings amplify the problem by giving the model time to generate more loops.

## Check List (30-Second Diagnosis)

- [ ] Is the model repeating the same phrase or type of phrase (farewell, filler, acknowledgment)?
- [ ] Does the repetition happen after a conversation-ending event (goodbye, transfer, hang up)?
- [ ] Are the timeouts or debounce settings longer than the expected speech duration?

If 2+ checks are "yes," this pattern likely matches.

## Examples

### Example 1: Farewell Loop
**Setup:** User says goodbye. Model responds "Goodbye!" but pipeline doesn't terminate for 10 seconds.
**Symptom:** Model says "Goodbye! ... Have a great day! ... Take care! ... Bye bye!" in a loop.
**Root cause:** No stop signal after the farewell. Model fills the silence with more output.
**Fix:** Set timeout to `max_expected_speech_duration + 1s`. Terminate pipeline immediately after end-of-conversation tool call.

### Example 2: Tool Call Repetition
**Setup:** Model calls `end_conversation()` tool. Pipeline processes the tool but doesn't disconnect.
**Symptom:** Model calls `end_conversation()` 3-4 more times.
**Root cause:** No disconnect after tool execution. Model interprets silence as "user waiting" and retries.
**Fix:** Add idempotency guard — first `end_conversation()` triggers disconnect. Subsequent calls are no-ops.

## Fix Strategy

1. Set timeouts to `expected_speech_duration + 1 second` (not generous 10-30 second defaults)
2. Set debounce shorter than the gap between repetitions
3. Add idempotency guards on all terminal tool handlers
4. Terminate the pipeline immediately after conversation-ending events

## Prevention

- Always define an explicit termination path for every conversation-ending scenario
- Use tight timeouts — generous timeouts enable loops
- Make terminal tool calls (end, transfer, hang up) idempotent
- Test the full lifecycle: greeting → conversation → farewell → disconnect

## Debugger Strategy

When an agent has access to a runtime debugger (PDB, JDB, or equivalent), use these targeted investigation steps instead of blind stepping.

**Breakpoints:**
- `end_conversation()` tool handler — Check whether `pipeline.disconnect()` or equivalent is called within this function on the first invocation
- `on_generation_complete()` or `_on_llm_response()` — Count how many times this fires after the farewell utterance

**Watch Expressions:**
- `pipeline.is_connected` — Should become `False` immediately after the farewell; if still `True` the stop path is missing
- `call(end_conversation, invocation_count)` — Increments past 1 confirms the idempotency guard is absent
- `timeout_ms` / `debounce_ms` — Values longer than the farewell utterance duration enable the loop

**Isolation Technique:**
Set a counter at the `on_generation_complete` breakpoint. If it fires more than once after the end-of-conversation event without a `disconnect()` call in between, the missing stop signal is confirmed.

**Expected Evidence:**
Confirms pattern: `on_generation_complete` fires 2+ times after farewell with `pipeline.is_connected == True` throughout. Rules it out: `disconnect()` is called inside the first `end_conversation()` invocation and generation does not fire again.

## Related Patterns

- **P17** — Context being spoken is a related "model speaks too much" issue
- **P05** — Flag duality (timeout values that need different settings in different contexts)
