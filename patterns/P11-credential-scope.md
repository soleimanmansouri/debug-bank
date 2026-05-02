---
id: P11
name: Credential Expression Scope Limitation
category: platform-quirks
severity: medium
frequency: occasional
---

# P11: Credential Expression Scope Limitation

## Pattern

A platform's credential interpolation (e.g., `$credentials.apiKey`) works in some contexts (headers, URL parameters) but silently fails in others (request body, nested objects). The expression renders as literal text instead of the credential value.

## Check List (30-Second Diagnosis)

- [ ] Is the credential value appearing as literal template text (e.g., `$credentials.apiKey` as a string)?
- [ ] Does the same credential expression work in a different field (e.g., headers)?
- [ ] Is the failing field a request body, JSON body, or nested object?

If 2+ checks are "yes," this pattern likely matches.

## Examples

### Example 1: Workflow Platform Body Interpolation
**Setup:** API key configured as `$credentials.apiKey` in the JSON request body.
**Symptom:** API returns 401 Unauthorized. Request body contains literal `$credentials.apiKey`.
**Root cause:** Workflow platform evaluates credentials in headers but not in `jsonBody` fields.
**Fix:** Use a pre-request script to inject the credential, or move authentication to headers.

### Example 2: Nested Config Interpolation
**Setup:** Database password configured as `${secrets.DB_PASS}` inside a nested YAML config.
**Symptom:** Connection fails with "wrong password." Logs show the literal template string.
**Root cause:** Secret interpolation only works at the top level of the config, not in nested objects.
**Fix:** Flatten the config to put secrets at the top level, or use environment variables directly.

## Fix Strategy

1. Test credential expressions with logging/echo to verify they resolve
2. If they fail in a specific context, check the platform's documentation for supported interpolation locations
3. Move credentials to a supported context (headers, environment variables)

## Prevention

- Always verify credential resolution in new contexts with a test request
- Prefer header-based authentication over body-based when the API supports both
- Document which platform contexts support interpolation

## Debugger Strategy

When an agent has access to a runtime debugger (PDB, JDB, or equivalent), use these targeted investigation steps instead of blind stepping.

**Breakpoints:**
- `request_builder.build_body` — inspect the request body object just before it is serialized and sent
- `credential_resolver.resolve` — confirm whether the resolver is even called for body fields

**Watch Expressions:**
- `request.body['apiKey']` (or equivalent key) — is the value the literal string `$credentials.apiKey` or the resolved secret?
- `request.headers['Authorization']` — compare: does the header resolve correctly while the body does not?

**Isolation Technique:**
Set a breakpoint on request send. Print the full serialized body. If the body contains a `$` or `{{` literal, the resolver was never invoked for that field. Then check whether the same expression in a header field resolves correctly — asymmetry confirms scope limitation.

**Expected Evidence:**
Confirms: body field value equals the raw template string (e.g., `"$credentials.apiKey"`). Header field for the same credential resolves to the actual key. Rules out: body field contains the real secret value.

## Related Patterns

- **P14** — Expression evaluation requiring a prefix is a related platform quirk
