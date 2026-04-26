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

## Related Patterns

- **P08** — Config chain gaps can cause fallback to error-like responses
