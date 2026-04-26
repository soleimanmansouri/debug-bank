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

## Related Patterns

- **P11** — Credential scope issues are another expression engine limitation
- **P14** — Expression prefix requirements are another expression engine quirk
