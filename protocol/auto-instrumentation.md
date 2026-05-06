# Auto-Instrumentation Fallback Protocol

A 6-step process for debugging when no pattern matches. Instead of guessing, instrument the code with hypothesis-tagged logging, capture runtime evidence, then extract a new pattern candidate.

## When to Use

- Symptom classifier returns "no match"
- All pattern checklist scores are 0/3
- Pattern bank search and domain catalog are both empty

Do not skip Step 0: always run the classifier first. This fallback only activates after a genuine no-match.

## The 6 Steps

### Step 1: Generate Hypotheses

Based on the symptom, generate 3-5 testable hypotheses. Tag each with H1, H2, H3, etc.

**Format:**
```
H1: [Cause statement] — Test: [specific observable that would confirm/reject]
H2: [Cause statement] — Test: [specific observable that would confirm/reject]
H3: [Cause statement] — Test: [specific observable that would confirm/reject]
```

**Rules:**
- Each hypothesis must be falsifiable with a specific test
- Rank by proximity to error site, then by frequency of that cause type
- Limit to 5 hypotheses — more dilutes focus

### Step 2: Instrument Code

For each hypothesis, add targeted debug logging at the relevant code sites.

**Wrapping format:**

Python:
```python
# region DEBUG-H1
import logging as _dbg; _dbg.basicConfig(filename='.debug-bank/debug.log', level=_dbg.DEBUG)
_dbg.debug(f"[DEBUG H1] variable_name={variable_name!r}")
# endregion DEBUG-H1
```

JavaScript / TypeScript:
```javascript
// #region DEBUG-H1
const _fs = require('fs'); _fs.appendFileSync('.debug-bank/debug.log', `[DEBUG H1] variable_name=${JSON.stringify(variable_name)}\n`);
// #endregion DEBUG-H1
```

Go:
```go
// #region DEBUG-H1
_f, _ := os.OpenFile(".debug-bank/debug.log", os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
fmt.Fprintf(_f, "[DEBUG H1] variable_name=%v\n", variable_name)
_f.Close()
// #endregion DEBUG-H1
```

**Rules:**
- Log ONLY to `.debug-bank/debug.log` — never to stdout (pollutes agent context)
- NEVER modify business logic — logging instrumentation only
- Log format: `[DEBUG Hn] variable_name=value`
- Ensure `.debug-bank/` directory exists before running: `mkdir -p .debug-bank`

### Step 3: Reproduce

Run the failing operation exactly as it fails in production.

- Use the exact inputs/conditions that trigger the bug
- Let the instrumented code capture evidence to `.debug-bank/debug.log`
- Do not interpret yet — capture first

**Output:** Populated `.debug-bank/debug.log`

### Step 4: Analyze

Read `.debug-bank/debug.log` and map each log entry to its hypothesis.

**Verdict format for each hypothesis:**
```
H1: CONFIRMED — logs show [specific value/behavior that confirms]
H2: REJECTED — logs show [specific value/behavior that rejects]
H3: INCONCLUSIVE — no relevant log entries captured
```

A hypothesis is CONFIRMED when the logged values match what its test predicted.
A hypothesis is REJECTED when the logged values contradict what its test predicted.
A hypothesis is INCONCLUSIVE when no relevant evidence was captured — add more instrumentation if needed.

### Step 5: Fix

Apply a minimal fix for the confirmed hypothesis only.

- Change as little as possible
- Verify the fix resolves the symptom
- Confirm no regressions in adjacent functionality

### Step 6: Extract Pattern Candidate

After the fix is verified, generate a pattern candidate from what you learned.

**Template:**
```yaml
candidate_id: P-candidate-YYYY-MM-DD
name: [short descriptive name extracted from root cause]
category: [inferred from symptom type: config / data / async / auth / type / state / network]
symptom_keywords:
  - [keyword from original symptom description]
  - [keyword from original symptom description]
checklist:
  - [derived from the hypothesis that confirmed — what to check first]
  - [derived from evidence that confirmed it — what log/value to look for]
  - [derived from what ruled out other hypotheses — the differentiating signal]
debugger_strategy:
  breakpoints:
    - [file:function — the instrumentation point that revealed the bug]
  watch_expressions:
    - [the log expression that showed the confirming evidence]
fix_summary: [one sentence describing the minimal fix]
```

**Storage:**
- If the MCP `debug_record` tool is available: store via that tool
- Otherwise: write to `debug-memory/candidates/P-candidate-YYYY-MM-DD.yaml` for human review

## Cleanup

After the fix is verified and the candidate is extracted, remove ALL instrumentation blocks.

```bash
# Python — remove region blocks and everything between them
grep -rn "# region DEBUG-H" . --include="*.py" -l | xargs -I{} sed -i '' '/# region DEBUG-H/,/# endregion DEBUG-H/d' {}

# JavaScript / TypeScript — remove region blocks
grep -rn "// #region DEBUG-H" . --include="*.js" --include="*.ts" -l | xargs -I{} sed -i '' '/\/\/ #region DEBUG-H/,/\/\/ #endregion DEBUG-H/d' {}

# Go — remove region blocks
grep -rn "// #region DEBUG-H" . --include="*.go" -l | xargs -I{} sed -i '' '/\/\/ #region DEBUG-H/,/\/\/ #endregion DEBUG-H/d' {}

# Verify nothing remains
grep -rn "DEBUG-H" . --include="*.py" --include="*.js" --include="*.ts" --include="*.go"
```

The last command should return empty. If not, remove the remaining blocks manually.

## Key Differentiator

Unlike standard instrumentation workflows, this protocol auto-extracts a pattern candidate after fixing. Every no-match bug that gets resolved feeds back into the pattern bank, making the classifier more accurate for future sessions. The pattern bank grows from real production bugs, not theoretical causes.
