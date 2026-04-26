# Debug Bank — Debug Trajectory Protocol

## Debugging Protocol

Follow this exact chain for every debugging session. Each step produces evidence for the next — never skip.

### Before Investigating

1. **Pattern Check** — Read `patterns/` for matching root cause type. If a match exists, verify the known fix applies before re-investigating. This takes 30 seconds and saves hours.
2. **Domain Search** — Search your domain catalogs (if any) for similar symptoms.

### The Trajectory

1. **Reproduce** — Get the exact error. Capture full output (logs, stack trace, HTTP status). If you can't reproduce, add logging and try again.
2. **Hypothesize** — State 2-3 possible root causes ranked by likelihood. Each hypothesis must be falsifiable with a specific test.
3. **Isolate** — Test hypotheses one at a time. Use binary search: disable half the system, check if bug persists, narrow.
4. **Diagnose** — Identify the single root cause. Trace the full call chain from trigger to symptom. Check for "root cause behind the root cause."
5. **Fix** — Minimal change. Verify the fix addresses the root cause, not a symptom.
6. **Record** — Add the trajectory to your domain catalog using this format:
   ```
   ### [Category] Short Title (date)
   - **Symptom:** What the user/system saw
   - **Root cause:** The actual technical cause
   - **Fix:** What was changed (file:line)
   - **Key insight:** The generalizable lesson
   - **Pattern:** P-number if it matches an existing pattern
   ```

## The 3-Exchange Rule

If 3 rounds of iterative fixing show no progress: **STOP.** Do not continue the same approach.

Instead:
- Re-plan from scratch with everything you now know
- Add logging/instrumentation to gather new evidence
- Switch strategy entirely (e.g., from code-level fix to config-level fix)

## Anti-Patterns (Enforced)

- **Never** fix a symptom without finding the root cause
- **Never** apply a fix you saw work elsewhere without verifying it matches the current root cause
- **Never** keep iterating past 3 exchanges — switch strategy
- **Never** assume you understand the bug from the description alone — always reproduce first
- **Always** check if 2+ symptoms share one root cause before filing separate fixes

## Feedback Capture

When a user corrects your approach, create a feedback rule:

```markdown
---
name: descriptive-rule-name
type: feedback
---
The rule itself — what to do or not do.

**Why:** The reason (what went wrong, what incident this prevents).
**How to apply:** When/where this rule activates.
```

Store feedback rules alongside your domain catalogs. Review them at session start.

## Session Discipline

- **Start of session:** Load pattern bank + relevant domain catalogs + feedback rules
- **During debugging:** Follow the trajectory protocol exactly
- **End of session:** Record all trajectories, update pattern bank if needed
- **After user correction:** Create feedback rule immediately
