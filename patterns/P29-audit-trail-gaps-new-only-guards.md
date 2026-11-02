---
id: P29
name: Audit-Trail Gaps and NEW-Only Trigger Guards
category: data-integrity
severity: critical
frequency: common
---

# P29: Audit-Trail Gaps and NEW-Only Trigger Guards

## Pattern

Regulated systems (e.g. a GMP eQMS under Part 11 / Annex 11) rely on DB triggers for the audit trail and for immutability of released records. Two gaps recur. (1) A new regulated table is created without the audit-trail trigger or immutability guard that every older table has: changes to it leave no trace. (2) A guard trigger only inspects the NEW row (`WHEN (NEW.status = 'released')`, `IF NEW.locked THEN`). An update that changes the state at the same time as the content (e.g. moving a record back to `draft` while editing it) passes the guard, because NEW no longer looks protected. The change is hidden from the very control meant to stop it.

## Check List (30-Second Diagnosis)

- [ ] Does the migration contain `CREATE TABLE` for GMP data but no audit trigger on that table?
- [ ] Does a guard trigger's `WHEN` clause or body reference `NEW.` but not `OLD.` on an UPDATE trigger?
- [ ] Can a single UPDATE change both the state column and protected content?
- [ ] Is there no read-back check in the migration that lists triggers per table?

If 2+ checks are "yes," this pattern likely matches.

## Examples

### Example 1: New Child Table Without Audit Trigger
**Setup:** A GMP eQMS added `change_control_items` as a child of an audited parent table.
**Symptom:** An inspector asked for the history of a deleted item; there was none.
**Root cause:** The migration created the table and RLS policies but no `AFTER INSERT OR UPDATE OR DELETE` audit trigger.
**Fix:** Added the audit trigger; added a CI check that every table in the regulated schema has one.

### Example 2: Back-to-Draft Bypass
**Setup:** `BEFORE UPDATE ... WHEN (NEW.status = 'approved') EXECUTE FUNCTION reject_content_change()`.
**Symptom:** Approved documents could be edited by setting `status = 'draft'` in the same request.
**Root cause:** The guard only looked at NEW; NEW.status was `draft`, so the trigger never fired.
**Fix:** `WHEN (OLD.status = 'approved')` plus an explicit rule for allowed transitions out of `approved`.

## Fix Strategy

1. List triggers per regulated table (`information_schema.triggers` / `pg_trigger`) and diff against the table list
2. Add the audit trigger to every table missing it
3. Rewrite guards to check OLD (what is protected) and NEW (what is allowed): protected if `OLD.state IN (locked states)`; transitions out of a locked state only via an explicit allow-list
4. Add a read-back block at the end of the migration that raises if a table lacks its audit trigger

## Prevention

- Template or helper for "new regulated table" that always includes audit trigger + immutability guard
- CI/DB test: every table in the regulated schema has an audit trigger; guard triggers on UPDATE reference `OLD.`
- Migration read-back: `DO $$ ... IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgrelid = 't'::regclass AND tgname LIKE '%audit%') THEN RAISE EXCEPTION ...`
- Pre-deploy scanner flags `CREATE TABLE` without an audit trigger in the diff and UPDATE triggers whose `WHEN` uses NEW only

## Debugger Strategy

**Breakpoints:**
- Not a debugger bug — query the catalog. In application code, break at the save handler for the protected entity to see the UPDATE payload.

**Watch Expressions:**
- `SELECT tgname, pg_get_triggerdef(oid) FROM pg_trigger WHERE tgrelid = 'tbl'::regclass AND NOT tgisinternal`
- The UPDATE payload: does it change the state column and content together?

**Isolation Technique:**
In a test DB, update a locked row while setting its state to an unlocked value in the same statement. If it succeeds, the guard is NEW-only.

**Expected Evidence:**
- **This pattern:** No audit row for the change, or the guard did not fire because NEW was already unlocked.
- **Not this pattern:** Audit row exists and guard fired, but the application suppressed the error.

## Related Patterns

- **P25** — Without an audit trail, values overwritten by a migration cannot be restored
- **P05** — Context-dependent flag: the same column means "protected" in OLD and "editable" in NEW
- **P21** — New table added next to existing ones, untested path
