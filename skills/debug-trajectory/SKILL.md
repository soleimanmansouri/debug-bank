---
name: debug-trajectory
description: Activate when debugging any bug or error. Enforces the 7-step debug trajectory protocol with pattern-first checking, 3-exchange stop rule, and trajectory recording.
version: 1.0.0
user-invocable: true
argument-hint: "[error description or symptom]"
---

# Debug Trajectory Protocol

You are now in debug trajectory mode. Follow this protocol exactly.

## Step 1: Pattern Check (DO THIS FIRST)

Before investigating, scan the pattern bank for a matching root cause type.

Read all files in the `patterns/` directory (or your project's pattern bank location). For each pattern, check if its symptoms match the current bug.

**If a pattern matches:**
- State which pattern (e.g., "This matches P08: Config Resolution Chain Gap")
- Read the full pattern file
- Apply the check list
- If the check list confirms, apply the fix strategy directly
- Skip to Step 6 (Fix) — no need for Steps 2-5

**If no pattern matches:**
- State "No pattern match" and proceed to Step 2

## Step 2: Reproduce

Get the exact error. Capture FULL output — never summarize.

- Run the failing operation
- Capture complete logs, stack traces, HTTP responses
- Include 50+ lines of surrounding context
- Record exact reproduction steps

If you can't reproduce, add temporary logging and try again. Do NOT proceed without reproduction.

## Step 3: Hypothesize

State 2-3 possible root causes, ranked by likelihood.

For each hypothesis:
- "If [hypothesis] is correct, then [specific test] would show [specific result]"

## Step 4: Isolate

Test hypotheses ONE AT A TIME. Binary search.

- Start with the most likely hypothesis
- Disable/enable components to narrow scope
- If 3 hypotheses fail → TRIGGER 3-EXCHANGE RULE (see below)

## Step 5: Diagnose

Identify the SINGLE root cause.

- Trace the full call chain: trigger → propagation → symptom
- Check for "root cause behind the root cause"
- Verify this cause explains ALL symptoms

## Step 6: Fix

Minimal change addressing the root cause.

- Change as little as possible
- Verify ALL symptoms resolved
- Check for regressions

## Step 7: Record

Add trajectory to your domain catalog:

```markdown
### [Category] Short Title (YYYY-MM-DD)
- **Symptom:** What was observed
- **Root cause:** The actual cause
- **Fix:** What was changed
- **Key insight:** Generalizable lesson
- **Pattern:** P-number or "New"
```

If the root cause represents a NEW pattern type, consider adding it as P20+.

## 3-Exchange Stop Rule

If 3 rounds of isolating/fixing show no progress:

1. **STOP.** Do not attempt round 4 with the same approach.
2. Choose one:
   - **Re-plan** from scratch with accumulated knowledge
   - **Add instrumentation** (logging, tracing) to gather new evidence
   - **Switch strategy level** (code → config → architecture)
3. The counter resets after switching strategy.

## Anti-Patterns (ENFORCED)

- NEVER fix a symptom without finding the root cause
- NEVER apply a fix from elsewhere without verifying it matches THIS root cause
- NEVER iterate past 3 exchanges on the same approach
- NEVER assume understanding from the description alone — reproduce first
- ALWAYS check if multiple symptoms share one root cause
