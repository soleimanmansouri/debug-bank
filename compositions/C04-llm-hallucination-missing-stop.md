---
id: C04
name: LLM Hallucination + Missing Stop Signal
patterns: [P04, P18]
frequency: common
severity: high
---

# C04: LLM Hallucination + Missing Stop Signal

## The Composition

**P04 (LLM Copies Example Text)** provides the wrong behavior: the model treats prompt examples as actions to perform.
**P18 (Loop Without Stop Signal)** provides persistence: the model keeps generating without a termination signal, amplifying the wrong behavior.

Alone, P04 causes a one-time wrong action (the model skips a step or says something from an example). Alone, P18 causes a loop of correct behavior. Together, they create an AI agent that confidently performs the wrong action in an infinite loop — the worst possible combination in a customer-facing system.

## Combined Check List

- [ ] Does the system prompt contain example dialogues or action sequences? (P04)
- [ ] Does the model perform actions that match the examples literally? (P04)
- [ ] Does the model keep generating after the conversation should have ended? (P18)
- [ ] Is there a timeout that's generous enough to allow extended output? (P18)
- [ ] Is the incorrect behavior repetitive rather than a one-time mistake? (composition)

If 3+ are "yes," this composition likely matches.

## Why They Amplify

P04 gives the model a wrong script. P18 ensures the model keeps following that script indefinitely:

1. System prompt contains: "Example: 'Your appointment is confirmed for Tuesday at 2pm'"
2. Model treats this as a completed action → skips actual confirmation step (P04)
3. Model reaches end of conversation, no explicit stop signal (P18)
4. Model fills silence with more "helpful" output → repeats confirmation variants endlessly
5. Caller hears: "Confirmed for Tuesday! ... Yes that's all set! ... Great, Tuesday at 2! ..." for 15 seconds

## Signature Symptoms

- **Model skips critical steps** AND continues talking after the conversation should end
- **Output contains verbatim text from the system prompt** repeated in variations
- **The behavior gets worse with longer timeouts** (more time = more wrong output)
- **Prompt engineering fixes P04 but P18 resurfaces** — you remove the example but the model still loops on something else

## Real-World Example

**Scenario:** Voice agent has example dialogue in system prompt showing appointment confirmation. Agent skips the confirmation step (P04) and enters a farewell loop repeating variants of "your appointment is confirmed" for 15 seconds (P18).

**How it was found:** Call recordings showed the agent speaking for 15+ seconds after the user said goodbye, all variations of the example confirmation text.

**Fix:** Removed example dialogues (P04 fix). Added explicit pipeline termination on `end_conversation` tool call with tight timeout of `speech_duration + 1s` (P18 fix). Added idempotency guard so the first `end_conversation` call disconnects and subsequent calls are no-ops.

## Investigation Strategy

1. **Record and replay the full output** — listen/read the entire model output, not just the error point
2. **Compare output against system prompt** — is the model quoting or paraphrasing examples?
3. **Check the termination mechanism** — how does the system decide the conversation is over?
4. **Test with minimal prompt** — remove all examples and check if the loop persists. If it stops, P04 was the content source. If it continues with different content, P18 is the dominant pattern.

## Prevention

- Never put action-like text in LLM prompts. Use structural enforcement (flow nodes, state machines) for critical steps
- Always set tight timeouts on voice/streaming models — `expected_duration + small_buffer`, not generous defaults
- Add an explicit termination mechanism (tool call + pipeline disconnect), not just "wait for the model to stop talking"
- Test with adversarial silence — if the user stops talking, does the agent stop within 3 seconds?

## Related Compositions

- **C05 (P19 + P05):** When P04 is fixed via prompt engineering but the fix breaks a different context (P05), and further prompt attempts fail (P19), switch to code-level enforcement
