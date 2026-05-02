---
id: PXX
name: Pattern Name Here
category: code-structure | data-integrity | configuration | dependencies | platform-quirks | llm-ai
severity: low | medium | high | critical
frequency: rare | occasional | common | very-common
---

# PXX: Pattern Name Here

## Pattern

One-paragraph description of the root cause type. What happens, structurally, that causes this class of bug?

## Check List (30-Second Diagnosis)

- [ ] First diagnostic question (yes/no answer)
- [ ] Second diagnostic question
- [ ] Third diagnostic question

If 2+ checks are "yes," this pattern likely matches.

## Examples

### Example 1: Brief Title
**Setup:** What the code/config looked like
**Symptom:** What was observed
**Root cause:** How this pattern manifested
**Fix:** What was changed

### Example 2: Brief Title
**Setup:** ...
**Symptom:** ...
**Root cause:** ...
**Fix:** ...

## Fix Strategy

1. First step to resolve
2. Second step
3. Verification step

## Prevention

How to avoid this pattern in new code:
- Coding practice or review check
- Automated check if possible

## Debugger Strategy

When an agent has access to a runtime debugger (PDB, JDB, GDB, or equivalent), use these targeted investigation steps instead of blind stepping.

**Breakpoints:**
- `function_or_method_name` — Why this breakpoint matters

**Watch Expressions:**
- `expression` — What to look for in the value

**Isolation Technique:**
One-line description of how to use the debugger to confirm or reject this pattern.

**Expected Evidence:**
What the debugger output looks like when this pattern is the root cause vs. when it isn't.

## Related Patterns

- **PXX** — Similar pattern, different context
- **PXX** — Often co-occurs with this pattern
