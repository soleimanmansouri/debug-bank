---
id: P14
name: Expression Evaluation Requires Prefix
category: platform-quirks
severity: low
frequency: occasional
---

# P14: Expression Evaluation Requires Prefix

## Pattern

A platform requires a special prefix (e.g., `=`, `$`, `{{`) for expression evaluation. Without the prefix, template expressions render as literal text instead of being evaluated.

## Check List (30-Second Diagnosis)

- [ ] Is a template expression (e.g., `{{ variable }}`) rendering as literal text in the output?
- [ ] Does adding a prefix character (like `=`) before the expression fix it?
- [ ] Do other fields in the same node evaluate expressions correctly (with the prefix)?

If 2+ checks are "yes," this pattern likely matches.

## Examples

### Example 1: Workflow Engine Requires = Prefix
**Setup:** Setting a field value to `{{ $json.email }}` in a workflow node.
**Symptom:** Output contains the literal string `{{ $json.email }}` instead of the email address.
**Root cause:** This platform requires `=` prefix for expression mode: `={{ $json.email }}`.
**Fix:** Add `=` prefix to the expression.

## Fix Strategy

1. Check the platform documentation for expression syntax requirements
2. Add the required prefix
3. Test with a simple expression first to verify

## Prevention

- When using a new platform, always test a simple expression first
- Document the platform's expression syntax in your project notes

## Debugger Strategy

When an agent has access to a runtime debugger (PDB, JDB, or equivalent), use these targeted investigation steps instead of blind stepping.

**Breakpoints:**
- `field_resolver.resolve` / the function that evaluates a node field's value — inspect raw field string and resolved output
- `node.execute` — check the final resolved parameter map before the node runs its logic

**Watch Expressions:**
- `field.raw_value` — the string as stored in the node config (e.g., `"{{ $json.email }}"`)
- `field.resolved_value` — what the runtime actually passes to the node
- `field.raw_value == field.resolved_value` — if True, no interpolation occurred

**Isolation Technique:**
At the resolver breakpoint, compare `raw_value` to `resolved_value`. If they are identical and `raw_value` contains a template expression, the resolver skipped this field. Then test the same expression with the required prefix (e.g., `=`) and re-run — watch for `resolved_value` to change to the interpolated result.

**Expected Evidence:**
Confirms: `raw_value` contains `{{ ... }}` or `$json.` and `resolved_value` is the same literal string — no substitution happened. Rules out: `resolved_value` differs from `raw_value` and contains the expected runtime data.

## Related Patterns

- **P11** — Credential scope limitations are another expression evaluation issue
- **P12** — Expression engine corruption is another expression processing issue
