# Debug Bank — Cross-Agent Instructions

This file provides the debug trajectory protocol for any AI coding agent (Codex CLI, Gemini CLI, Cursor, Windsurf, etc.).

## Core Protocol

### Before Investigating Any Bug

1. Read files in `patterns/` directory for matching root cause patterns (P01-P21+)
2. Search `examples/` for similar symptoms in domain catalogs
3. Only then start: Reproduce → Hypothesize → Isolate → Diagnose → Fix → Record

### The 7-Step Trajectory

| Step | Action | Output |
|------|--------|--------|
| 1. Pattern Check | Scan pattern bank for matching root cause | Match or no-match (30 seconds) |
| 2. Reproduce | Get exact error with full output | Logs, stack trace, HTTP status |
| 3. Hypothesize | 2-3 ranked, falsifiable root causes | Ordered list with test for each |
| 4. Isolate | Test hypotheses one at a time | Narrowed to single area |
| 5. Diagnose | Identify single root cause, trace call chain | Root cause statement |
| 6. Fix | Minimal change addressing root cause | Code diff |
| 7. Record | Add trajectory to domain catalog | Structured entry |

### Stop Rule

If 3 rounds of iterative fixing show no progress, STOP. Re-plan from scratch or switch strategy.

### Recording Format

After fixing, add to the relevant domain catalog:

```markdown
### [Category] Short Title (YYYY-MM-DD)
- **Symptom:** What was observed
- **Root cause:** The actual technical cause
- **Fix:** What was changed
- **Key insight:** The generalizable lesson
- **Pattern:** P-number if matches existing pattern
```

### Feedback Rules

When corrected by a user, create a persistent rule:

```markdown
Rule statement.

**Why:** The reason this matters.
**How to apply:** When/where to apply this rule.
```

## Agent-Specific Notes

### Codex CLI
- Store patterns in `.codex/patterns/` or project root `patterns/`
- Reference this file as `AGENTS.md` in your project root

### Gemini CLI
- Store patterns in `.gemini/patterns/` or project root `patterns/`
- Gemini CLI reads `AGENTS.md` automatically

### Cursor
- Add the CLAUDE.md content to your `.cursorrules` file
- Store patterns in project root `patterns/`

### Windsurf
- Add protocol to `.windsurfrules`
- Store patterns in project root `patterns/`
