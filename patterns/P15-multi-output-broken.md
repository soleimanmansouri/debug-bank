---
id: P15
name: Multi-Output Node Rejects Valid Returns
category: platform-quirks
severity: medium
frequency: rare
---

# P15: Multi-Output Node Rejects Valid Returns

## Pattern

A workflow platform's multi-output node configuration (`numberOutputs > 1`) rejects valid return formats when using batch execution mode. The node expects a specific array structure that doesn't match the documentation.

## Check List (30-Second Diagnosis)

- [ ] Does the node have `numberOutputs` set to > 1?
- [ ] Does the node use `runOnceForAllItems` (batch) execution mode?
- [ ] Does the error mention invalid return format despite matching the docs?

If all 3 checks are "yes," this pattern likely matches.

## Examples

### Example 1: Code Node Multi-Output Failure
**Setup:** A code node with `numberOutputs: 3` and `runOnceForAllItems: true`. Returns `[output1Items, output2Items, output3Items]`.
**Symptom:** Node rejects the return with "invalid output format" error.
**Root cause:** Platform bug — batch mode with multiple outputs doesn't support nested array returns even though the API suggests it should.
**Fix:** Replace with parallel single-output nodes, each with a filter condition.

## Fix Strategy

1. Split multi-output logic into parallel single-output nodes
2. Use filter/switch nodes to route items to the correct output
3. If possible, use `runOnceForEachItem` mode instead of batch mode

## Prevention

- Test multi-output nodes with minimal examples before building complex logic
- Prefer single-output nodes with downstream routing for reliability

## Debugger Strategy

When an agent has access to a runtime debugger (PDB, JDB, or equivalent), use these targeted investigation steps instead of blind stepping.

**Breakpoints:**
- `node_runner.validate_output` — the internal function that checks return value structure before routing to outputs
- `code_node.execute` — capture the exact return value from user code before the platform processes it

**Watch Expressions:**
- `return_value` — is it `[[...], [...], [...]]` (nested array) or `[..., ..., ...]` (flat)?
- `type(return_value[0])` — is the first element an array of items or a single item?
- `node.numberOutputs` and `node.runOnceForAllItems` — confirm both flags are set

**Isolation Technique:**
At the validate_output breakpoint, compare `return_value` structure against what the validator's expected schema says. Reduce to a minimal repro: two outputs, one item each, simplest possible return shape. If the validator still rejects it, the bug is in the platform's batch+multi-output interaction, not user code structure.

**Expected Evidence:**
Confirms: `return_value` matches documented format but validator throws "invalid output format" with `runOnceForAllItems=true` and `numberOutputs > 1`. Rules out: validator accepts the return when `runOnceForAllItems=false` with the same structure.

## Related Patterns

- **P16** — Binary data handling is another platform-specific data format issue
