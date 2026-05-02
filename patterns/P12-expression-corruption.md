---
id: P12
name: Expression Engine Corrupts Non-JSON Bodies
category: platform-quirks
severity: high
frequency: occasional
---

# P12: Expression Engine Corrupts Non-JSON Bodies

## Pattern

A workflow or automation platform's expression engine assumes all request bodies are JSON. When processing XML, YAML, plain text, or other formats, the engine corrupts the body by attempting to parse or template it.

## Check List (30-Second Diagnosis)

- [ ] Is the request body in a non-JSON format (XML, YAML, plain text)?
- [ ] Is the body corrupted, truncated, or re-formatted after passing through the platform?
- [ ] Does a hardcoded (non-templated) body work correctly?

If 2+ checks are "yes," this pattern likely matches.

## Examples

### Example 1: XML-RPC Body Mangled
**Setup:** An XML-RPC API call with body `<?xml version="1.0"?>...` passed through a workflow engine.
**Symptom:** API returns "malformed XML" error.
**Root cause:** Expression engine tries to evaluate `<?xml...` as a template expression, corrupting the body.
**Fix:** Use a JSON-based API endpoint instead. If XML is required, base64-encode the body and decode in a pre-request step.

### Example 2: YAML Config Upload Reformatted
**Setup:** Uploading a YAML config file through a workflow platform's HTTP node.
**Symptom:** YAML indentation is destroyed, causing parse errors.
**Root cause:** Expression engine normalizes whitespace in the body.
**Fix:** Upload as binary/file attachment instead of inline body.

## Fix Strategy

1. Verify the body format before and after the platform processes it
2. Use JSON-based APIs when available (most modern APIs support JSON)
3. If non-JSON is required, bypass the expression engine (binary upload, pre-encoded, or raw passthrough mode)

## Prevention

- Prefer JSON APIs in workflow automation platforms
- Test non-JSON bodies with a request inspector before connecting to the real API
- Check if the platform has a "raw body" mode that bypasses expression evaluation

## Debugger Strategy

When an agent has access to a runtime debugger (PDB, JDB, or equivalent), use these targeted investigation steps instead of blind stepping.

**Breakpoints:**
- `expression_engine.process` / the method that transforms the body before sending — capture input and output
- `http_node.execute` — inspect the body both before and after the node's internal processing step

**Watch Expressions:**
- `body_before` — the raw body string as provided by the user
- `body_after` — the body string after expression engine processing
- `body_before == body_after` — if False and body is XML/YAML, corruption confirmed

**Isolation Technique:**
Hardcode a static non-templated XML or YAML body (no `{{` or `$` expressions) and observe whether the engine still mutates it. If a static body also gets corrupted, the engine is unconditionally processing the content type. Then compare byte-for-byte using `repr()` or hex dump to catch invisible whitespace changes.

**Expected Evidence:**
Confirms: `body_before != body_after` — XML tags altered, indentation collapsed, or special characters escaped. Rules out: bodies are identical byte-for-byte after processing.

## Related Patterns

- **P11** — Credential scope issues are another expression engine limitation
- **P14** — Expression prefix requirements are another expression engine quirk
