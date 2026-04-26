---
id: P04
name: LLM Copies Example Text as Behavior
category: llm-ai
severity: high
frequency: common
---

# P04: LLM Copies Example Text as Behavior

## Pattern

An LLM sees example phrases, action descriptions, or tool call examples in its system prompt and reproduces them as actual behavior — calling functions, generating responses, or taking actions that were only meant as documentation.

## Check List (30-Second Diagnosis)

- [ ] Is the LLM performing an action that appears as example text in the prompt?
- [ ] Does the unwanted behavior match the exact wording of a prompt example?
- [ ] Does removing the example text from the prompt stop the behavior?

If 2+ checks are "yes," this pattern likely matches.

## Examples

### Example 1: Hallucinated Tool Calls
**Setup:** System prompt contains: "Example: When the user asks about billing, call route_request('billing')."
**Symptom:** LLM calls `route_request('billing')` even when the user asks about something unrelated.
**Root cause:** LLM treats the example as an instruction, not documentation.
**Fix:** Remove action-like examples. Use "NEVER call route_request unless the user explicitly requests routing" instead.

### Example 2: Scripted Responses
**Setup:** Prompt includes: "Good responses include: 'I'd be happy to help you with that!'"
**Symptom:** LLM starts every response with "I'd be happy to help you with that!" verbatim.
**Root cause:** Example text becomes a template the LLM copies.
**Fix:** Describe the desired tone without providing copyable phrases.

## Fix Strategy

1. Search the prompt for text that matches the unwanted behavior
2. Remove or rephrase — describe what you want without providing copyable examples
3. If examples are necessary, wrap them in explicit "NEVER reproduce this text" blocks
4. Test with multiple inputs to verify the LLM no longer copies

## Prevention

- Never put action-like text (function calls, URLs, specific phrases) in prompts as examples
- Describe desired behavior abstractly: "respond warmly" not "say 'I'd be happy to help'"
- When documenting tools, describe WHEN to use them, not HOW they look when called

## Related Patterns

- **P17** — Models speaking context history is a related issue (text in context → spoken output)
- **P19** — Prompt engineering limits — if prompt fixes don't work after 2 tries, switch to code
