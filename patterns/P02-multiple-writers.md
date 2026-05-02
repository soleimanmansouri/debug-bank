---
id: P02
name: Multiple Write Sources → Data Corruption
category: data-integrity
severity: critical
frequency: common
---

# P02: Multiple Write Sources → Data Corruption

## Pattern

Two or more code paths write to the same field, table, or file. One path overwrites the other's work, causing data loss or corruption. Often hidden because each writer works correctly in isolation.

## Check List (30-Second Diagnosis)

- [ ] Is the corrupted data written by more than one code path?
- [ ] Does the bug appear intermittently or only under specific timing?
- [ ] Do both writers produce valid data individually, but the result is wrong?

If 2+ checks are "yes," this pattern likely matches.

## Examples

### Example 1: Transcript Overwrite
**Setup:** Two systems record conversation transcripts — a context manager saves `context.messages`, and an observer saves `observer.transcript_turns`.
**Symptom:** Final transcript is missing turns, or has duplicate entries depending on timing.
**Root cause:** Both write to the same `transcript` field in the database. The last writer wins.
**Fix:** Designate a single authoritative writer. The other system reads from it instead of writing independently.

### Example 2: Concurrent Cache Updates
**Setup:** Two background jobs update the same cache key — one refreshes pricing, one refreshes inventory.
**Symptom:** Cache sometimes shows stale pricing or stale inventory.
**Root cause:** Jobs run on overlapping schedules. Each reads the full cache entry, updates its portion, and writes back — overwriting the other's update.
**Fix:** Use atomic field-level updates instead of full-entry overwrites. Or use separate cache keys.

## Fix Strategy

1. Grep for ALL writes to the affected target (field, table, file, cache key)
2. Identify which writer should be authoritative
3. Convert other writers to readers, or use upsert/merge instead of overwrite
4. Add a constraint or lock if concurrent writes are unavoidable

## Prevention

- Establish single-writer patterns for critical data
- Use database constraints (unique keys, check constraints) to catch duplicate writes
- Log write sources with metadata to detect multi-writer situations early

## Debugger Strategy

When an agent has access to a runtime debugger (PDB, JDB, or equivalent), use these targeted investigation steps instead of blind stepping.

**Breakpoints:**
- `context_manager.save` (or equivalent write method) — Conditional: `if field == "transcript"`
- `observer.save_transcript_turn` — Break on every call to capture the full call stack at write time

**Watch Expressions:**
- `db.transcript` (or `context.messages`) — Snapshot the value before and after each write
- `len(observer.transcript_turns)` — Track turn count across writes to detect overwrite vs. append behavior
- `inspect.stack()` — At each write breakpoint, capture the full call stack to identify which code path triggered it

**Isolation Technique:**
Set a conditional breakpoint on the write target and log `id(caller)` or the stack frame source file at each hit. If two distinct stack frames both write to the same field, the pattern is confirmed. Temporarily disable one writer and verify the data is correct — then re-enable to confirm the overwrite.

**Expected Evidence:**
Confirms pattern: two separate stack traces both reach the same write target within one request/event cycle, and the second write's value does not include data from the first. Rules it out: only one call stack path ever reaches the write target.

## Related Patterns

- **P09** — Auto-apply pipelines are a specific case of unwanted writes
- **P08** — Config chain gaps can cause fallback to a different writer
