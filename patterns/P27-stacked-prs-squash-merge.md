---
id: P27
name: Stacked PRs Conflict After Parent Squash Merge
category: merge-workflow
severity: medium
frequency: common
---

# P27: Stacked PRs Conflict After Parent Squash Merge

## Pattern

PR B is branched from PR A's branch (a "stack"). A is merged with squash, so main gets one new commit whose content equals A but whose history does not contain A's commits. B still carries A's original commits. Git sees A's changes twice (once squashed on main, once as individual commits in B) and reports conflicts in every file A touched, even though nothing truly conflicts. Resolving them by hand under time pressure leads to P28.

## Check List (30-Second Diagnosis)

- [ ] Was the conflicting PR's base branch another PR's branch?
- [ ] Was that parent PR merged with "squash and merge"?
- [ ] Are the conflicting files exactly the files the parent PR changed?
- [ ] Does `git log origin/main..B` still list the parent's commits?

If 2+ checks are "yes," this pattern likely matches.

## Examples

### Example 1: Three-Level Stack
**Setup:** Feature split into A (schema), B (API), C (UI), each based on the previous branch. Repository enforces squash merge.
**Symptom:** After A merged, B and C showed conflicts in all schema files; after B merged, C conflicted again.
**Root cause:** Squash rewrote A's and B's commits; the children still contained the originals.
**Fix:** `git rebase --onto origin/main A B` (replay only B's own commits), then the same for C.

### Example 2: Retargeted Base Without Rebase
**Setup:** The hosting platform retargeted B's base to main automatically after A merged.
**Symptom:** B's diff suddenly showed A's changes as well, plus conflicts.
**Root cause:** Same as above; retargeting does not remove the parent commits.
**Fix:** Merged origin/main into B and resolved by keeping main's version for A's files only after checking each hunk (see P28).

## Fix Strategy

1. Merge parents first, in order
2. For each child: `git rebase --onto origin/main <old-parent-tip> <child>` or `git merge origin/main` into the child
3. Re-run the full test suite on the child; review the resulting diff against main, not against the old parent

## Prevention

- Avoid stacks when the repo uses squash merge; prefer independent PRs off main
- If stacks are needed, use a tool that restacks after squash, or use merge commits for stacked parents
- Merge order is part of the PR description ("merge after #A")

## Debugger Strategy

**Breakpoints:**
- Not a runtime bug — use git as the debugger

**Watch Expressions:**
- `git log --oneline origin/main..<child>` — parent commits still listed means stale stack
- `git range-diff <parent-tip>...<child> origin/main...<child>` — shows which commits are duplicates

**Isolation Technique:**
`git cherry -v origin/main <child>` — commits marked `+` that belong to the parent are the cause.

**Expected Evidence:**
- **This pattern:** Conflicts limited to files the parent changed; parent commits still present in the child.
- **Not this pattern:** Conflicts in files only the child and a third PR touched (real conflict).

## Related Patterns

- **P28** — The usual (wrong) way these conflicts get resolved
- **P26** — Parallel PR flows also cause migration timestamp collisions
