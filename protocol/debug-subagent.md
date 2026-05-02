# Debug Subagent Protocol — Debug Bank v3

## 1. Purpose

Debug2Fix (arXiv:2602.18571) showed that giving agents access to PDB/JDB via a subagent architecture improves fix rates by 12-22%. But their approach is brute-force — the subagent starts from scratch every time. This protocol integrates Debug Bank's pattern library so the subagent gets targeted breakpoints and watch expressions from day one.

The result: fewer steps to diagnosis, higher-quality fixes (from canonical pattern solutions), and graceful fallback to exploratory mode for novel bugs.

---

## 2. Architecture

```
Main Agent (owns the fix)
  │
  ├─ Step 1: Symptom → Classifier (classifier/symptom-classifier.md)
  │   └─ Output: Ranked pattern matches + debugger strategies
  │
  ├─ Step 2: Delegate to Debug Subagent
  │   └─ Input: Hypothesis + pattern's debugger_strategy
  │   └─ Tools: debug_start_session, debug_control, debug_inspect, debug_breakpoint
  │   └─ Output: Confirmed/rejected hypothesis with evidence
  │
  ├─ Step 3: Fix (main agent applies canonical fix from pattern)
  │
  └─ Step 4: Verify (subagent runs regression test)
```

The main agent retains ownership of the fix decision. The subagent is read-only + debugger-only — it cannot edit files or spawn nested subagents.

---

## 3. Subagent Interface

Four tools are available to the debug subagent, matching Debug2Fix's tool set with pattern-guided extensions.

### `debug_start_session(test_command, breakpoints[])`

Builds the project, runs the failing test, attaches the debugger, and sets initial breakpoints.

```python
debug_start_session(
    test_command="pytest tests/test_transcript.py::test_concurrent_write -xvs",
    breakpoints=[
        {"file": "transcript_manager.py", "line": 42},
        {"file": "observer.py", "line": 18}
    ]
)
# breakpoints come from the matched pattern's debugger_strategy field
# Returns: { session_id, initial_state, build_status }
```

### `debug_control(session_id, action)`

Controls execution flow. Valid actions: `continue`, `step_over`, `step_into`, `step_out`.

```python
debug_control(
    session_id="dbg-abc123",
    action="step_into"
)
# Returns: { file, line, function, status }
```

### `debug_inspect(session_id, target, expression?)`

Queries program state at the current execution point. Valid targets: `locals`, `expression`, `call_stack`, `object_fields`.

```python
debug_inspect(
    session_id="dbg-abc123",
    target="expression",
    expression="transcript._writer_id"
)
# watch expressions come from the matched pattern's debugger_strategy field
# Returns: { value, type, location }
```

```python
debug_inspect(
    session_id="dbg-abc123",
    target="call_stack"
)
# Returns: [{ frame, file, line, function, locals_summary }, ...]
```

### `debug_breakpoint(session_id, action, location, condition?)`

Manages breakpoints at runtime. Valid actions: `set`, `remove`.

```python
debug_breakpoint(
    session_id="dbg-abc123",
    action="set",
    location={"file": "transcript_manager.py", "line": 67},
    condition="self._writer_id != previous_writer_id"
)
# Conditional breakpoints are essential for patterns like P02
# (break only when the writer changes, not on every access)
# Returns: { breakpoint_id, status }
```

---

## 4. Pattern-Guided Delegation Protocol

When the classifier returns a match, the main agent constructs a delegation message and hands off to the subagent. The delegation format depends on match confidence.

### High-confidence match (2+ checklist items confirmed)

```
Main → Subagent:

Pattern: P02 (Multiple Writers)
Confidence: high

Set breakpoints:
  - transcript_manager.py:42 (write entry point)
  - observer.py:18 (secondary write path)

Watch expressions:
  - transcript._writer_id
  - transcript._last_modified_by
  - id(current_frame.f_locals['self'])

Expected evidence if P02 confirmed:
  - transcript._writer_id changes across consecutive calls
  - two distinct self references reach the write method
  - call stack shows observer.py and context_manager.py both in chain

Task: Confirm or reject P02. Return structured evidence (see Evidence Format).
If confirmed, stop — do not attempt fix.
If rejected, return counter-evidence and halt.
```

### Low-confidence match (1 checklist item confirmed)

```
Main → Subagent:

Pattern: P08 (Config Chain Gap) — low confidence
One matching signal: config reads return None at runtime despite file present

Start by setting breakpoints on the config resolution chain:
  - config_loader.py at each resolution step
  - Watch: resolved_value, source_path, fallback_triggered

If P08 is ruled out (config chain resolves cleanly), switch to exploratory mode:
  1. Break at the error site, inspect all locals
  2. Walk the call stack frame by frame
  3. Check variable state at each frame for unexpected None, wrong types, stale values

Return: diagnosis with evidence, whether P08 or an alternative root cause.
```

### No pattern match

```
Main → Subagent:

No pattern matched. Run exploratory debugging:

1. Break at the reported error site (file, line from stack trace)
2. Inspect all locals at that frame
3. Walk up the call stack — inspect state at each frame
4. Set breakpoints at entry points of functions in the call chain
5. Flag any anomalies: unexpected None, wrong types, stale/mutated values, missing keys

Return: suspected root cause with supporting evidence.
Do not attempt a fix — diagnosis only.
```

---

## 5. Subagent Limits

- **Max 25 steps per session** — matches Debug2Fix's cap. Each `debug_control` or `debug_inspect` call counts as one step.
- **25 steps reached without conclusion** — return partial evidence tagged `verdict: inconclusive`. Main agent re-plans with new hypotheses.
- **No file edits** — subagent has read-only access plus debugger tools. No `Edit`, `Write`, or shell mutations.
- **No nested subagents** — flat hierarchy. The subagent cannot spawn further subagents. All re-delegation goes back through the main agent.
- **Single session scope** — one failing test per session. If multiple failures need investigation, the main agent opens separate sessions sequentially.

---

## 6. Evidence Format

The subagent returns a structured YAML block. The main agent parses this to decide whether to apply the canonical fix or re-investigate.

```yaml
hypothesis: "P02 — Multiple Writers to transcript field"
verdict: confirmed         # confirmed | rejected | inconclusive
confidence: high           # high | medium | low
evidence:
  - type: variable_state
    location: "transcript_manager.py:42"
    observed: "transcript._writer_id changes from 'context_manager' to 'observer' across calls"
    expected: "single writer identity throughout test"
  - type: call_stack
    location: "observer.py:18 → pipeline.py:55 → transcript_manager.py:42"
    observation: "observer reaches write method via pipeline callback, bypassing the designated writer"
  - type: expression_result
    expression: "id(self) == id(context_manager_instance)"
    location: "transcript_manager.py:42 (second hit)"
    observed: "False — self is observer instance"
    expected: "True — only context_manager should reach this line"
breakpoints_used: 3
steps_used: 12
suggested_fix: "Designate context_manager as single authoritative writer. Gate transcript_manager.write() on writer identity check. See P02 canonical fix."
```

**Verdict semantics:**

| Verdict | Meaning | Main agent action |
|---|---|---|
| `confirmed` | Evidence matches pattern's expected signals | Apply canonical fix from pattern |
| `rejected` | Evidence contradicts pattern | Run next ranked hypothesis |
| `inconclusive` | Steps exhausted or ambiguous state | Re-plan with partial evidence as new context |

---

## 7. Comparison: Pattern-Guided vs. Brute-Force

| Metric | Debug2Fix (brute-force) | Debug Bank v3 (pattern-guided) |
|---|---|---|
| Starting knowledge | None — explores blindly | Pattern match provides targeted breakpoints |
| Avg breakpoints needed | 8-15 (trial and error) | 2-4 (from pattern's debugger_strategy) |
| Steps to diagnosis | 15-25 | 5-12 (estimated) |
| Fix quality | 66% correct (34% wrong fix) | Higher — canonical fix from validated pattern library |
| Novel bugs | Full capability | Falls back to exploratory mode (same capability) |
| Infrastructure required | PDB / JDB | Same — PDB / JDB |

The pattern-guided approach does not sacrifice capability on novel bugs — it simply adds a fast path for known bug classes. When no pattern applies, the subagent runs the same exploratory loop Debug2Fix uses.

---

## 8. Integration with Debug Trajectory Protocol

This subagent protocol slots into Steps 2-4 of the 7-step debug trajectory defined in `debug-trajectory.md`. The remaining steps stay with the main agent.

| Step | Owner | What changes |
|---|---|---|
| 1 — Pattern Check | Main agent | Unchanged — classifier runs before subagent is invoked |
| 2 — Reproduce | **Subagent** | Subagent runs failing test with debugger attached via `debug_start_session` |
| 3 — Hypothesize | Main agent + classifier | Classifier provides ranked hypotheses with pattern IDs and debugger strategies |
| 4 — Isolate | **Subagent** | Subagent uses pattern-specific breakpoints to confirm or reject each hypothesis |
| 5 — Diagnose | Main agent | Main agent reads evidence, selects root cause |
| 6 — Fix | Main agent | Main agent applies canonical fix (or novel fix for unmatched patterns) |
| 7 — Record | Main agent | Unchanged — pattern library updated if new pattern discovered |

### Delegation trigger

The main agent delegates to a subagent at Step 4 when:

1. Reproduction is confirmed (Step 2 passed), AND
2. A hypothesis exists (from classifier or manual analysis), AND
3. The hypothesis requires runtime state to confirm (static analysis alone is insufficient)

If static analysis is sufficient to confirm the root cause (e.g., a missing import, a typo in a key name), skip the subagent — direct fix is faster.

---

## 9. Implementation Notes

### Attaching PDB programmatically

```python
import pdb
import subprocess

def debug_start_session(test_command: str, breakpoints: list[dict]) -> dict:
    # Inject breakpoint() calls or use pytest --pdb
    # For programmatic control, use pdb.Pdb() instance with custom stdin/stdout
    debugger = pdb.Pdb(stdout=capture_stream)
    # Set initial breakpoints from pattern strategy
    for bp in breakpoints:
        debugger.set_break(bp["file"], bp["line"])
    # Run test under debugger
    ...
```

### Conditional breakpoints

PDB supports conditions natively:

```python
debugger.set_break("transcript_manager.py", 42, cond="self._writer_id != prev_writer_id")
```

This is the key mechanism for P02-style patterns where you only want to break on state transitions, not every access.

### Session isolation

Each `debug_start_session` call should fork a fresh process. Do not reuse debugger state across hypotheses — stale breakpoints from a previous hypothesis can corrupt evidence for the next one.
