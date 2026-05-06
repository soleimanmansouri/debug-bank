---
name: auto-instrument
description: Fallback debugging when no pattern matches — hypothesis-driven code instrumentation with auto pattern extraction
trigger: "no pattern match" OR "classifier returned no matches" OR manual invocation
---

# Auto-Instrument Skill

Use when the symptom classifier returns no match and the domain catalog is empty. Do NOT skip Step 0.

## Step 0: Confirm No Match

Verify the classifier was already run. Expected output: "No pattern match" or all checklist scores 0/3.
If you haven't run the classifier yet, do that first.

## Step 1: Generate Hypotheses

```
H1: [cause] — Test: [what log value would confirm this]
H2: [cause] — Test: [what log value would confirm this]
H3: [cause] — Test: [what log value would confirm this]
```

Rank by proximity to the error site. Max 5 hypotheses.

## Step 2: Instrument

Ensure the log directory exists: `mkdir -p .debug-bank`

**Python**
```python
# region DEBUG-H1
import logging as _dbg; _dbg.basicConfig(filename='.debug-bank/debug.log', level=_dbg.DEBUG)
_dbg.debug(f"[DEBUG H1] var={var!r}")
# endregion DEBUG-H1
```

**JavaScript / TypeScript**
```javascript
// #region DEBUG-H1
const _fs = require('fs'); _fs.appendFileSync('.debug-bank/debug.log', `[DEBUG H1] var=${JSON.stringify(var)}\n`);
// #endregion DEBUG-H1
```

**Go**
```go
// #region DEBUG-H1
_f, _ := os.OpenFile(".debug-bank/debug.log", os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
fmt.Fprintf(_f, "[DEBUG H1] var=%v\n", var)
_f.Close()
// #endregion DEBUG-H1
```

Rules: log ONLY to `.debug-bank/debug.log`, never stdout. Never modify business logic.

## Step 3: Reproduce

Run the failing operation. Logs capture evidence per hypothesis.

## Step 4: Analyze

Read `.debug-bank/debug.log`. For each hypothesis:
```
H1: CONFIRMED / REJECTED / INCONCLUSIVE — [evidence]
```

## Step 5: Fix

Minimal fix for the confirmed hypothesis only. Verify it resolves the symptom.

## Step 6: Extract Pattern Candidate

```yaml
candidate_id: P-candidate-YYYY-MM-DD
name: [from root cause]
category: [config / data / async / auth / type / state / network]
symptom_keywords: [from symptom]
checklist:
  - [confirmed hypothesis — what to check first]
  - [log expression that revealed it]
  - [signal that ruled out other hypotheses]
debugger_strategy:
  breakpoints: [file:function where bug was found]
  watch_expressions: [log expression that showed the evidence]
fix_summary: [one sentence]
```

Store via MCP `debug_record` tool if available, otherwise write to `debug-memory/candidates/`.

## Cleanup

```bash
grep -rn "# region DEBUG-H" . --include="*.py" -l | xargs -I{} sed -i '' '/# region DEBUG-H/,/# endregion DEBUG-H/d' {}
grep -rn "// #region DEBUG-H" . --include="*.js" --include="*.ts" --include="*.go" -l | xargs -I{} sed -i '' '/\/\/ #region DEBUG-H/,/\/\/ #endregion DEBUG-H/d' {}
grep -rn "DEBUG-H" . --include="*.py" --include="*.js" --include="*.ts" --include="*.go"
```

Last command must return empty. See `protocol/auto-instrumentation.md` for full specification.
