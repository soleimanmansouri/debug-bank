---
id: P25
name: Data Migration Rewrites Signed Content
category: data-integrity
severity: critical
frequency: occasional
---

# P25: Data Migration Rewrites Signed Content

## Pattern

Electronic signatures (e.g. 21 CFR Part 11 / EU GMP Annex 11) store a content hash computed over a defined set of columns of the signed record. A later data migration "cleans up" values in exactly those columns: renaming an enum value, normalising text, back-filling a field that is part of the hash. The migration succeeds and the UI looks fine, but every existing signature on a touched row now verifies as "record changed after signing". Nobody changed the GMP content, yet the system can no longer prove that, and the signature manifestation is broken for every affected record.

## Check List (30-Second Diagnosis)

- [ ] Did signature verification start failing right after a deploy with migrations?
- [ ] Do the failing signatures all belong to rows the migration touched (same table, same value range)?
- [ ] Does the migration contain `UPDATE <signed_table> SET <col> = ...` where `<col>` is in the signature hash field list?
- [ ] Is the hash recomputed from the current row instead of a stored snapshot?

If 2+ checks are "yes," this pattern likely matches.

## Examples

### Example 1: Enum Rename in a Status-Like Content Column
**Setup:** A GMP eQMS signs complaint records. The hash covers `category`, among other columns. A product decision renamed category `minor` to `low`.
**Symptom:** After the release, every signed complaint with the old category showed "content changed since signature" in the audit view.
**Root cause:** The migration ran `UPDATE complaints SET category = 'low' WHERE category = 'minor'` on signed rows. The hash was recomputed from the new value at verify time.
**Fix:** Migration reverted for signed rows (values restored from the audit trail); the legacy value is mapped to the new label in code (`display_category('minor') -> 'low'`).

### Example 2: Back-Fill of a Hashed Column
**Setup:** A new NOT NULL column was added and back-filled with a default on all rows, and the column was also added to the current hash field list.
**Symptom:** Old signatures failed verification even though their own field-list version did not include the column.
**Root cause:** Verification used the *current* field list instead of the version stored with the signature (see P26), so the back-fill entered the old hashes.
**Fix:** Verification always uses the field-list version recorded at signing time; the back-fill was limited to unsigned rows.

## Fix Strategy

1. List the hashed columns for each signed table and the field-list version stored with each signature
2. Diff the migration against that list: any `UPDATE` / `ALTER COLUMN ... TYPE ... USING` on a hashed column of a signed row is the culprit
3. Restore original values on signed rows from the audit trail (never "re-sign" silently)
4. Map legacy values to new ones in application code or a view, not in the stored row
5. Re-run signature verification over all signed rows and compare with the pre-migration result

## Prevention

- Rule: never modify signed columns on signed rows. Restrict data migrations with `WHERE <signed_marker> IS NULL` or skip the column entirely
- A migration test that signs fixture rows, runs the migration, and asserts that the old signatures still verify
- A DB guard (trigger) that rejects updates to hashed columns once a row is signed
- Pre-deploy scanner flags `UPDATE ... SET` in migration files and diffs that touch hash field lists

## Debugger Strategy

**Breakpoints:**
- The signature verify function (e.g. `verify_signature`, `compute_record_hash`) — inspect which columns and values enter the hash

**Watch Expressions:**
- `hash_input` / canonical JSON of the row at verify time vs. the snapshot at signing time — the differing key is the migrated column
- The field-list version used for verification vs. the one stored on the signature

**Isolation Technique:**
Restore a pre-migration DB snapshot, verify one affected signature (passes), apply only the suspect migration, verify again (fails) — then diff the hash inputs.

**Expected Evidence:**
- **This pattern:** Hash inputs differ only in columns the migration wrote; the signer and timestamp are untouched.
- **Not this pattern:** Hash inputs differ in columns written by application code after signing (look at P02 / workflow fields) or the field list itself changed (P26).

## Related Patterns

- **P26** — Field-list version drift produces the same "changed" symptom without any data change
- **P29** — Without an audit trigger the original values cannot be restored
- **P02** — Another writer (not a migration) changes signed columns
