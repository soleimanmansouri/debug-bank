---
id: P19
name: Prompt Engineering Has Hard Limits
category: llm-ai
severity: high
frequency: common
---

# P19: Prompt Engineering Has Hard Limits

## Pattern

Iterative prompt fixes fail because the model's behavior (especially in voice/multimodal modes) doesn't respect text-level constraints. "Don't say X," markers, non-speakable tags, and format instructions are all ignored by the generation layer.

## Check List (30-Second Diagnosis)

- [ ] Have you tried 2+ prompt variations to fix the same behavior?
- [ ] Does the unwanted behavior persist regardless of how the instruction is phrased?
- [ ] Is this a voice, multimodal, or streaming model (not a standard text completion)?

If all 3 checks are "yes," this pattern likely matches. Stop prompt engineering and switch to code.

## Examples

### Example 1: Voice Model Ignores Constraints
**Setup:** Prompt says "NEVER say the phrase 'Is there anything else?'" but model keeps saying it.
**Symptom:** 5 prompt variations all fail. Model continues the behavior.
**Root cause:** Voice generation layer doesn't process negative constraints from system prompt.
**Fix:** Add post-processing filter in the pipeline code to catch and suppress the phrase.

### Example 2: Streaming Model Ignores Format Instructions
**Setup:** Prompt says "Always respond with bullet points" but streaming output is paragraphs.
**Symptom:** Format instruction works in batch mode but not in streaming mode.
**Root cause:** Streaming generation optimizes for fluency over format compliance.
**Fix:** Add a post-processing step that reformats streaming output.

## Fix Strategy

1. After 2 failed prompt attempts, STOP prompt engineering
2. Identify the behavior you want to control
3. Implement it at the pipeline/code level instead:
   - Output filtering (suppress unwanted phrases)
   - Event guards (prevent unwanted actions)
   - Post-processing (reformat output)
   - Timeout controls (limit generation duration)
4. Reserve prompt engineering for WHAT the model says, not HOW it generates

## The 2-Attempt Rule

- Attempt 1: Clear, direct instruction in the system prompt
- Attempt 2: Restructured prompt with different framing
- If both fail: Switch to code-level solution. Do NOT try attempts 3, 4, 5.

This rule exists because prompt fixes for generation-layer issues have a near-zero success rate after the second attempt. Every additional attempt wastes time without adding information.

## Prevention

- For voice/multimodal models, default to code-level controls for behavioral constraints
- Use prompts for content and personality, not behavioral guardrails
- Test constraints with adversarial inputs before assuming they work

## Debugger Strategy

When an agent has access to a runtime debugger (PDB, JDB, or equivalent), use these targeted investigation steps instead of blind stepping.

**Breakpoints:**
- `_build_system_prompt()` or `get_system_message()` — Verify the constraint text is actually present in the assembled prompt string before it reaches the model
- `post_process_output()` or `on_text_delta()` — Break here to check whether any output filter/guard exists for the unwanted phrase or behavior

**Watch Expressions:**
- `system_prompt` (the final assembled string) — Search for the constraint keyword; its absence here means a prompt assembly bug, not a generation-layer limit
- `output_filters` or `guards` list — An empty list confirms there is no code-level enforcement

**Isolation Technique:**
Confirm the constraint IS present in the final prompt string, then let generation proceed. If the unwanted behavior appears despite the constraint being in the prompt, this is a generation-layer issue — switch to a code-level filter.

**Expected Evidence:**
Confirms pattern: constraint keyword found in `system_prompt`, unwanted behavior still present in output. Rules it out: constraint missing from `system_prompt` — that's a prompt assembly bug (P04), not a generation-layer limit.

## Related Patterns

- **P17** — Context being spoken is often the specific issue prompt engineering can't fix
- **P18** — Looping is another generation-layer behavior that needs code-level solutions
- **P04** — Example text being copied is a prompt-level issue that CAN be fixed with prompt changes
