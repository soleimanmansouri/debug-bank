---
id: C05
name: Prompt Limits + Flag Duality
patterns: [P19, P05]
frequency: occasional
severity: medium
---

# C05: Prompt Limits + Flag Duality

## The Composition

**P05 (Context-Dependent Flag Duality)** provides the conflict: the same setting needs opposite values in different contexts.
**P19 (Prompt Engineering Has Hard Limits)** provides the ceiling: no amount of prompt rewriting can resolve the conflict because the LLM interprets instructions differently across contexts.

Alone, P05 is resolvable — you add context-aware branching. Alone, P19 tells you to switch from prompt to code. Together, they create a prompt engineering trap: you fix the behavior in context A, it breaks in context B, you fix B, it breaks A, and after 2 attempts you realize prompt-level solutions cannot express "do X in context A but Y in context B" reliably.

## Combined Check List

- [ ] Does a prompt fix for one scenario break a different scenario? (P05)
- [ ] Have you attempted 2+ prompt rewrites that each fix one case and break another? (P19)
- [ ] Does the same instruction need opposite interpretation in different contexts? (P05)
- [ ] Is the context difference subtle enough that the LLM can't reliably distinguish? (P19)

If 3+ are "yes," this composition likely matches.

## Why They Amplify

P05 demands context-awareness: "do X here, Y there." P19 shows that the LLM can't reliably distinguish "here" from "there" via prompt text alone:

1. **Attempt 1:** Add "always confirm appointments before booking" → works for new appointments, but for rescheduling the model asks for confirmation on every step (annoying)
2. **Attempt 2:** Add "only confirm final booking, not intermediate steps" → rescheduling works, but new appointments skip confirmation again
3. **Attempt 3:** Add detailed conditional — model sometimes follows it, sometimes doesn't, depending on conversation length and context window position

The LLM is not a rule engine. Conditional logic expressed in natural language is fundamentally unreliable for edge cases.

## Signature Symptoms

- **Oscillating bug:** Fix A breaks B, fix B breaks A
- **Prompt grows longer with each attempt** — more conditions, more exceptions, more fragility
- **Works in testing, fails in production** — test conversations are short and controlled; production conversations have varied context
- **"It works 80% of the time"** — the 20% failure is exactly the context where the flag needs the opposite value

## Real-World Example

**Scenario:** Voice agent needs to confirm appointments before booking (new) but NOT re-confirm when the user explicitly says "book that one" during rescheduling. Prompt-level attempts to distinguish these two contexts failed after 3 iterations. Each rewrite fixed one scenario and regressed the other.

**How it was resolved:** Moved confirmation logic from prompt to flow-level enforcement. A state machine node checks: `if state == "rescheduling" and user_confirmed_in_previous_turn: skip_confirmation()`. The prompt was simplified to "follow the flow," and the flow handles the conditional logic deterministically.

## Investigation Strategy

1. **Count your prompt attempts.** If you've rewritten the same instruction 2+ times and each fix breaks a different scenario, you've hit P19.
2. **Identify the flag.** What behavior needs to be different across contexts? State it as: "In context A: do X. In context B: do Y."
3. **Test if the LLM can reliably distinguish A from B** with a simple prompt. If it can't distinguish the contexts >95% of the time, prompt engineering won't solve it.
4. **Move the logic to code.** The LLM's job becomes "follow the flow" and the code handles conditional branching deterministically.

## Prevention

- Default to code-level enforcement for any behavior that's conditional on conversation state
- Prompts should describe WHAT the agent does, not conditional IF/THEN rules
- If you find yourself writing "except when..." or "unless the user has already..." in a prompt, that logic belongs in a state machine
- Limit prompt engineering to 2 attempts per behavioral fix. If 2 rewrites don't converge, switch to code.

## Related Compositions

- **C04 (P04 + P18):** Often the examples added to the prompt to "teach" the LLM the conditional behavior trigger P04 (model copies the example literally) — adding a third pattern to the composition
