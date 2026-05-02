---
id: P13
name: Parse Code Matches Errors as Success
category: platform-quirks
severity: high
frequency: occasional
---

# P13: Parse Code Matches Errors as Success

## Pattern

Data extraction code (regex, XPath, CSS selector) matches both valid data and error responses. The parser extracts an error code, error message, or fallback value and treats it as successful data.

## Check List (30-Second Diagnosis)

- [ ] Is extracted data suspiciously short, numeric-only, or formatted like an error code?
- [ ] Does the extraction regex/selector match BOTH the success and error response format?
- [ ] Is there an error check BEFORE data extraction?

If check 3 is "no" and either 1 or 2 is "yes," this pattern likely matches.

## Examples

### Example 1: Regex Matches Error Code as ID
**Setup:** Extracting user ID with regex `/\d+/` from an API response.
**Symptom:** Some "user IDs" are actually HTTP error codes (404, 500) or fault codes.
**Root cause:** Regex matches any number — including error codes in error response bodies.
**Fix:** Check HTTP status code and response structure BEFORE extracting data. Only extract from confirmed success responses.

### Example 2: XPath Matches Error Banner
**Setup:** Extracting product price with XPath `//span[@class='price']`.
**Symptom:** Price is "$0.00" for out-of-stock items.
**Root cause:** Error page has a span with class "price" showing "$0.00" in the "unavailable" banner.
**Fix:** First check for error indicators (out-of-stock banner, error class), then extract only from success pages.

## Fix Strategy

1. Add an error check BEFORE data extraction (HTTP status, error fields, error indicators)
2. Make extraction patterns more specific — match the success format exactly, not broadly
3. Validate extracted data against expected format (range checks, type checks)

## Prevention

- Always check for errors before extracting data — never assume a response is successful
- Use schema validation on responses before extraction
- Test extraction against both success AND error responses

## Debugger Strategy

When an agent has access to a runtime debugger (PDB, JDB, or equivalent), use these targeted investigation steps instead of blind stepping.

**Breakpoints:**
- `extract_value` / the regex or XPath function that pulls data from the response — inspect `raw_response` before the pattern is applied
- Entry point of the success handler — confirm that an HTTP status check was passed before reaching this code

**Watch Expressions:**
- `response.status_code` — is it 2xx, or an error code like 404/500?
- `raw_response[:500]` — does the content look like an error page or fault XML, not a success payload?
- `match.group(0)` — is the extracted value a short numeric string that matches an error code format?

**Isolation Technique:**
At the extraction breakpoint, check `response.status_code` before examining the match. If the status is an error code and extraction still proceeds, there is no pre-extraction error guard. Then check whether the regex matches the error message text — run `re.findall(pattern, error_response_sample)` in the REPL to confirm.

**Expected Evidence:**
Confirms: `response.status_code` is 4xx/5xx and the extracted value equals an error code or error message fragment. Rules out: status is 2xx and extracted value matches expected data format (e.g., a full UUID, a dollar-prefixed price).

## Related Patterns

- **P08** — Config chain gaps can cause fallback to error-like responses
