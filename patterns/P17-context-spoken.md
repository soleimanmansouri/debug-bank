---
id: P17
name: Model Speaks Everything in Context
category: llm-ai
severity: high
frequency: common
---

# P17: Model Speaks Everything in Context

## Pattern

A multimodal or voice-enabled LLM treats conversation history messages as speakable content. Seeding assistant messages in context causes the model to speak that text aloud. Text-level instructions ("don't repeat this") are ignored by the audio generation layer.

## Check List (30-Second Diagnosis)

- [ ] Is the model producing unexpected speech that matches text in the conversation context?
- [ ] Was conversation history seeded before the first user interaction?
- [ ] Do "don't say this" instructions fail to prevent the speech?

If 2+ checks are "yes," this pattern likely matches.

## Examples

### Example 1: Greeting Spoken From Context
**Setup:** Voice agent initialized with `messages=[{"role": "assistant", "content": "Welcome, how can I help?"}]` to provide context.
**Symptom:** Model speaks "Welcome, how can I help?" at random times, not just at the start.
**Root cause:** Audio model treats all assistant messages in context as speakable. The seeded message gets re-spoken.
**Fix:** Initialize with empty context. Use system instructions for behavioral guidance, not seeded messages.

### Example 2: Example Phrases Spoken Aloud
**Setup:** System prompt contains imperative examples: "Say: Hello, how can I help you today?"
**Symptom:** Model speaks the exact example phrase as its greeting.
**Root cause:** Voice model reads imperative text ("Say X") as an instruction to literally say X.
**Fix:** Use declarative instructions ("The greeting should be warm and professional") instead of imperative examples.

## Fix Strategy

1. Initialize voice/multimodal models with empty conversation context
2. Use system instructions for behavioral guidance, not seeded assistant messages
3. Avoid imperative phrasing ("say X", "respond with Y") in system prompts for voice models
4. Test by checking if any text in the system prompt appears verbatim in speech output

## Prevention

- Never seed conversation history for voice/multimodal models
- Use declarative system instructions, not imperative examples
- Test voice output for unintended verbatim repetition of prompt text

## Debugger Strategy

When an agent has access to a runtime debugger (PDB, JDB, or equivalent), use these targeted investigation steps instead of blind stepping.

**Breakpoints:**
- `build_messages()` or equivalent context assembly function — Inspect the `messages` list before it's sent to the model; look for any `{"role": "assistant", ...}` entries that were seeded rather than generated
- `on_audio_output()` or `_handle_tts_frame()` — Break here to see which message text triggered the speech frame

**Watch Expressions:**
- `messages[-1]["content"]` — Does the spoken text match this or an earlier seeded entry?
- `[m for m in messages if m["role"] == "assistant"]` — Lists all assistant turns; any entry here before the first user message is a seed

**Isolation Technique:**
Clear the messages list (or replace seeded entries with empty strings) at the breakpoint, then resume. If the unwanted speech disappears, the seeded message is confirmed as the source.

**Expected Evidence:**
Confirms pattern: spoken audio text matches a seeded assistant message in `messages`. Rules it out: all assistant messages were generated in-session and `messages[0]["role"] == "user"`.

## Related Patterns

- **P04** — LLM copying examples is the text-only version of this pattern
- **P19** — Prompt engineering limits apply especially to voice/multimodal models
