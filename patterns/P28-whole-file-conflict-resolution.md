---
id: P28
name: Whole-File Conflict Resolution Drops Main's Changes
category: merge-workflow
severity: high
frequency: common
---

# P28: Whole-File Conflict Resolution Drops Main's Changes

## Pattern

A merge or rebase conflict is resolved by taking one side of the whole file (`git checkout --ours/--theirs`, "Accept all incoming", copying the file from another branch). The conflict disappears, CI may even be green, but every change that main received from *other* PRs in that file since the merge base is silently reverted. The lost change resurfaces later as a "regression" with no commit that obviously removed it.

## Check List (30-Second Diagnosis)

- [ ] Did a previously fixed behaviour come back right after a merge that had conflicts?
- [ ] Was any conflicted file resolved with `--ours`, `--theirs`, or a full-file copy?
- [ ] Does `git diff <merge-base> origin/main -- <file>` show hunks that are missing in the merged result?
- [ ] Does `git log -p` show the lost lines being removed in a merge commit (not a normal commit)?

If 2+ checks are "yes," this pattern likely matches.

## Examples

### Example 1: Audit Hook Lost in a Route File
**Setup:** PR X added a validation to `routes/records.py`; PR Y, branched earlier, also edited that file and conflicted after X merged.
**Symptom:** X's validation disappeared from production a day after Y merged.
**Root cause:** Y's author resolved with `git checkout --ours routes/records.py`, restoring Y's whole file.
**Fix:** Re-applied X's hunk; added a test for X's validation so a future drop fails CI.

### Example 2: Lock File Taken Wholesale
**Setup:** Two PRs added different dependencies.
**Symptom:** Import error after deploy for the first PR's dependency.
**Root cause:** Lock file conflict resolved with `--theirs`; first PR's entry vanished.
**Fix:** Regenerated the lock file from the merged manifest.

## Fix Strategy

1. For each file resolved in the merge: `git diff $(git merge-base HEAD origin/main) origin/main -- <file>` — this is what main changed
2. Confirm every one of those hunks is present in the merge result
3. Resolve conflicts hunk by hunk (`git mergetool`, or edit markers by hand), never by whole-file checkout
4. Run tests that cover main's recent changes in that file

## Prevention

- Ban `--ours/--theirs` on source files in the team's merge guide; allow only for generated files that are regenerated afterwards
- Review merge commits with `git show --remerge-diff <merge>` (git ≥ 2.36) to see how conflicts were resolved
- Every bug fix gets a regression test, so a silent revert fails CI
- Pre-deploy scanner flags leftover conflict markers and `--ours/--theirs` in scripts

## Debugger Strategy

**Breakpoints:**
- Not a runtime bug first — use git. Then break at the function whose fix vanished to confirm the old code is running.

**Watch Expressions:**
- `git log -S '<lost line>' --oneline -- <file>` — the last commit touching it is the merge that dropped it
- `git show --remerge-diff <merge-commit> -- <file>` — shows the resolution chosen

**Isolation Technique:**
`git log -S` on a line from the lost fix; if the removing commit is a merge commit, this pattern is confirmed.

**Expected Evidence:**
- **This pattern:** Lines removed in a merge commit with no corresponding intent in the PR description.
- **Not this pattern:** Lines removed in a normal commit (intentional revert or P22 regression).

## Related Patterns

- **P27** — Stacked PRs produce the conflicts that tempt whole-file resolution
- **P22** — A fix "undone" by later fixes looks similar but happens in normal commits
- **P02** — Two writers (PRs) to the same file; last writer wins
