# The Debug Trajectory Protocol

A 7-step chain for every debugging session. Each step produces evidence for the next. Never skip steps — the protocol's value comes from its completeness.

## Why This Exists

AI coding agents fail at debugging because they:
- Jump to fixes without understanding the root cause
- Apply fixes from unrelated bugs without verification
- Circle through the same failed approaches repeatedly
- Don't record what they learn, so the next session starts from zero

This protocol forces evidence-based debugging and captures every trajectory for future reuse.

## The 7 Steps

### Step 1: Pattern Check (30 seconds)

Before investigating, scan the pattern bank (P01-P19+) for a matching root cause type.

**How:**
- Read the symptom description
- Scan pattern titles and check-lists for matches
- If a pattern matches, read its full entry and verify the known fix applies to this specific case

**Output:** "Matches P08 (Config Chain Gap)" or "No pattern match — proceeding to reproduce."

**Why this step exists:** Most bugs in a mature codebase match a known pattern. Checking takes 30 seconds. Re-investigating takes hours.

### Step 2: Reproduce

Get the exact error with full output. No summarizing, no paraphrasing.

**How:**
- Run the failing operation and capture complete output
- Include 50+ lines of surrounding context for stack traces
- If you can't reproduce, add temporary logging and try again
- Record exact steps to reproduce

**Output:** Full error output, reproduction steps.

**Why this step exists:** "I think the bug is X" without reproduction leads to fixing symptoms. Reproduction forces you to see the actual failure.

### Step 3: Hypothesize

State 2-3 possible root causes, ranked by likelihood. Each must be falsifiable.

**How:**
- Based on the error output, list possible causes
- For each: "If this is the cause, then [specific observable test] would show [specific result]"
- Rank by: proximity to the error site, frequency of this cause type, simplicity

**Output:** Ordered list of hypotheses with falsification tests.

**Why this step exists:** Jumping straight to "the fix" without hypotheses means you're guessing. Multiple hypotheses prevent fixation on the first idea.

### Step 4: Isolate

Test hypotheses one at a time using binary search.

**How:**
- Start with the most likely hypothesis
- Disable/enable half the system to narrow the scope
- Check if the bug persists after each change
- Move to the next hypothesis only if the current one is falsified

**Output:** "Hypothesis 2 confirmed: the bug is in [specific component/function]."

**Why this step exists:** Testing all hypotheses at once produces ambiguous results. Binary search converges faster than shotgun debugging.

### Step 5: Diagnose

Identify the single root cause and trace the full call chain.

**How:**
- From the isolated component, trace the full path: trigger → propagation → symptom
- Check for "root cause behind the root cause" — the surface cause often has a deeper cause
- Verify this single cause explains ALL observed symptoms (not just the primary one)

**Output:** Root cause statement with call chain.

**Critical check:** If 2+ symptoms exist, verify they share one root cause before creating separate fixes. Multiple symptoms from one cause is common.

### Step 6: Fix

Minimal change that addresses the root cause, not a symptom.

**How:**
- Change as little as possible
- Verify the fix addresses the diagnosed root cause specifically
- Test that all symptoms are resolved (not just the one you noticed first)
- Check for regressions in adjacent functionality

**Output:** Code change with verification.

**Why minimal:** Every extra line is a potential new bug. Fix the root cause, nothing more.

### Step 7: Record

Add the trajectory to the relevant domain catalog.

**Format:**
```markdown
### [Category] Short Title (YYYY-MM-DD)
- **Symptom:** What the user/system observed
- **Root cause:** The actual technical cause (be specific — file, function, line if possible)
- **Fix:** What was changed
- **Key insight:** The generalizable lesson that helps next time
- **Pattern:** P-number if it matches an existing pattern, or "New — candidate for P20+"
```

**Why this step exists:** Without recording, the next debugging session starts from zero. With recording, the pattern bank grows and the agent gets faster.

## The Loop

After every fix:
1. Record the trajectory (Step 7)
2. Check if the root cause matches an existing pattern — if so, note the ID
3. If it's a NEW pattern type, consider adding it as a new P-number
4. Review: did the 7-step protocol help? What would you do differently?

This is how the system compounds. Every bug makes the next one faster to fix.
