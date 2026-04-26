# The 3-Exchange Stop Rule

## Rule

If 3 rounds of iterative fixing show no progress toward resolving a bug, **STOP immediately**. Do not attempt a 4th round with the same approach.

## Why This Exists

The most expensive failure mode of AI coding agents is circular debugging: attempting variations of the same approach repeatedly, each time hoping a small tweak will work. This burns tokens, wastes time, and produces no useful evidence.

In production debugging data, bugs that aren't resolved within 3 targeted attempts almost never resolve on attempt 4-7 with the same strategy. They resolve when the strategy changes.

## What Counts as an "Exchange"

One exchange = one hypothesis tested with a specific, observable result.

**This is 3 exchanges:**
1. "The bug is in the config file" → tested → config is correct
2. "The bug is in the API call" → tested → API response is valid
3. "The bug is in the parser" → tested → parser output matches input

**This is NOT 3 exchanges (it's 1 exchange, repeated 3 times):**
1. "Try adding a null check" → didn't fix it
2. "Try a different null check" → didn't fix it
3. "Try moving the null check earlier" → didn't fix it

The rule applies to distinct hypotheses, not variations of the same fix.

## What to Do When You Stop

### Option A: Re-Plan From Scratch
Start over with fresh eyes. Write down:
- Everything you now know (from the 3 failed attempts)
- What you've ruled out
- What you haven't checked

Then form completely new hypotheses.

### Option B: Add Instrumentation
Instead of guessing, add temporary logging/tracing to gather evidence:
- Print variable state at key points
- Log entry/exit of suspected functions
- Add timing information to identify where delays occur

Run the failing operation again and let the data tell you where the bug is.

### Option C: Switch Strategy Level
If you've been debugging at the code level, move up:
- Code-level fix not working? → Try config-level fix
- Config-level not working? → Try architecture-level change
- Prompt-level not working? → Try pipeline/code-level solution

This is especially relevant for LLM-based systems where prompt engineering has hard limits (see Pattern P19).

## Anti-Patterns

| Anti-Pattern | Why It's Harmful |
|---|---|
| "Let me try one more thing" (4th time) | Sunk cost fallacy. You're not making progress. |
| Tweaking the same variable repeatedly | Same hypothesis, not a new exchange |
| Blaming the framework without evidence | Unfalsiable hypothesis — can't lead to a fix |
| "This should work" without testing | Untested hypothesis doesn't count as an exchange |
| Asking the user to test manually each round | Offloads debugging work without adding information |

## Integration With the Trajectory Protocol

The 3-exchange rule sits between Steps 4 (Isolate) and 5 (Diagnose):

```
Step 4: Isolate (attempt 1)
  → No progress?
Step 4: Isolate (attempt 2, different hypothesis)
  → No progress?
Step 4: Isolate (attempt 3, different hypothesis)
  → No progress?
  
STOP. Choose Option A, B, or C above.
```

After the strategy switch, the counter resets. You get 3 fresh exchanges with the new approach.
