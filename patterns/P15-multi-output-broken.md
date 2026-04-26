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

## Related Patterns

- **P16** — Binary data handling is another platform-specific data format issue
