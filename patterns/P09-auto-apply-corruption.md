---
id: P09
name: Auto-Apply Pipeline Writing Feedback as Data
category: data-integrity
severity: critical
frequency: occasional
---

# P09: Auto-Apply Pipeline Writing Feedback as Data

## Pattern

An automated pipeline reads feedback, descriptions, or free-text content and writes it directly as structured data. The pipeline treats human-readable text as machine-actionable data, corrupting the target.

## Check List (30-Second Diagnosis)

- [ ] Is there an automated pipeline that processes free-text input into structured fields?
- [ ] Does the corrupted data look like a description or feedback rather than a proper value?
- [ ] Does the pipeline lack validation for the structural format of its output?

If 2+ checks are "yes," this pattern likely matches.

## Examples

### Example 1: Review Text Becomes System Prompt
**Setup:** A feedback pipeline reads change request descriptions and applies them to system configuration.
**Symptom:** System prompt suddenly contains a paragraph of review feedback instead of an instruction.
**Root cause:** Pipeline mapped CR description field to `system_prompt` field without validation.
**Fix:** Add structural validation — system prompts must match expected format (min/max length, required sections). Reject free-text that doesn't match.

### Example 2: Comment Becomes Database Value
**Setup:** An automation reads GitHub PR descriptions and updates a configuration database.
**Symptom:** Config value is "Fixed the bug in the login flow" instead of a valid setting.
**Root cause:** Pipeline extracted the first line of the PR description as the config value.
**Fix:** Add format validation — config values must match an enum or pattern. Log and skip invalid values.

## Fix Strategy

1. Identify where the pipeline reads free-text
2. Add structural validation between read and write (format checks, length limits, enum validation)
3. Add a review/approval step for automated writes to critical fields
4. Log all automated writes with source and value for audit

## Prevention

- Never write free-text directly to structured fields without validation
- Use separate pipelines for "read feedback" and "apply changes"
- Add minimum structural requirements (length, format, required fields) to all automated write targets

## Debugger Strategy

When an agent has access to a runtime debugger (PDB, JDB, or equivalent), use these targeted investigation steps instead of blind stepping.

**Breakpoints:**
- `pipeline.write_field` / the function that assigns a value to the structured target field — catch the write before it commits
- `pipeline.read_source` — inspect what text is being ingested from the feedback source

**Watch Expressions:**
- `target_value` — does the string look like a sentence/paragraph, not a valid config value?
- `len(target_value)` — free-text is usually far longer than a valid structured value
- `source_field_name` — confirm whether the field being read is a free-text field (e.g., `description`, `comment`)

**Isolation Technique:**
Step from the read to the write without executing any transformation step. If no transformation exists, that absence is the bug — free-text is flowing directly to a structured field.

**Expected Evidence:**
Confirms: `target_value` is a sentence or paragraph (e.g., "Fixed the bug in the login flow"). Rules out: `target_value` matches an expected enum, pattern, or short structured token.

## Related Patterns

- **P02** — Auto-apply is a specific case of an unwanted writer
