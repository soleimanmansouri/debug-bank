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

## Related Patterns

- **P17** — Context being spoken is a related "model speaks too much" issue
- **P05** — Flag duality (timeout values that need different settings in different contexts)
