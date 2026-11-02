---
id: P26
name: Signature Field-List Version Ordered by Migration File Name
category: configuration
severity: high
frequency: occasional
---

# P26: Signature Field-List Version Ordered by Migration File Name

## Pattern

The set of columns covered by an e-signature hash is versioned, and each version is tied to the migration that introduced its columns. The "current" version, or the version that applies to a signature, is derived from the migration file NAME order (timestamp prefix). Two parallel PRs pick the same or out-of-order timestamps. After both merge, sorting by name places a new column into an older, already released version, or makes the wrong version "current". Released signatures now hash over a different field list and verify as changed, or new signatures silently omit content.

## Check List (30-Second Diagnosis)

- [ ] Is the field-list version (or "current" version) selected by sorting migration names/timestamps?
- [ ] Do two or more migration files share the same timestamp prefix?
- [ ] Was a migration merged whose timestamp is OLDER than one already released?
- [ ] Did a released version's field list change in the diff (lines added to an old version)?

If 2+ checks are "yes," this pattern likely matches.

## Examples

### Example 1: Same Timestamp in Two Parallel PRs
**Setup:** A GMP eQMS keeps `FIELDS[entity][migration_name] = "col_a col_b"` and builds version N from all migrations sorted up to its anchor. Two PRs both generated `20260101120000_*.sql`.
**Symptom:** After merging both, signatures made the day before verified as "changed" for one entity.
**Root cause:** The second PR's name sorted *before* the anchor of the released version, so its column slid into that version's field list.
**Fix:** Renamed the late migration to a reserved, later slot; pinned the released version's field list in a test.

### Example 2: Back-Dated Migration From a Long-Lived Branch
**Setup:** A branch opened weeks ago carried a migration with its creation-day timestamp.
**Symptom:** "Current" version resolved to an older version after merge; new signatures lacked the new content field.
**Root cause:** Max-by-name picked the most recent *name*, not the most recently added version.
**Fix:** "Current" is an explicit constant, asserted to be the highest in a test.

## Fix Strategy

1. Print every version with its anchor migration and resolved field list; compare with the released (tagged) state
2. Find the migration whose name sorts into a released range and move it to a new, strictly later slot
3. Make the current version an explicit constant instead of "highest by name"
4. Re-verify all signatures and confirm no released version's field list changed

## Prevention

- Reserve strictly increasing timestamp slots per signature version up front; one slot per PR
- Pin test: every released version's field list is frozen (exact string), versions are strictly ordered, and `CURRENT == max(versions)`
- CI check: no two migration files may share a timestamp prefix
- Pre-deploy scanner flags duplicate migration timestamps and diffs touching hash field lists

## Debugger Strategy

**Breakpoints:**
- The function that resolves a signature's field list (e.g. `fields_for(entity, version)`) — inspect the sorted migration list it walks

**Watch Expressions:**
- `sorted(migrations)` around the version anchor — look for a name that should be later
- `CURRENT_VERSION` vs. `max(VERSIONS)`

**Isolation Technique:**
Resolve the field list for one released version on the last release tag and on the current commit; diff the two lists.

**Expected Evidence:**
- **This pattern:** Same version id, different field list between tag and HEAD; offending migration has a colliding or back-dated prefix.
- **Not this pattern:** Field lists identical, but stored row values differ (P25).

## Related Patterns

- **P25** — Same "signature changed" symptom caused by data, not by field lists
- **P02** — Multiple writers to the same config map (parallel PRs) without coordination
- **P27** — Parallel/stacked PR flows make timestamp collisions likely
