---
domain: api-integration
description: Third-party API calls, webhooks, authentication, rate limiting, and data synchronization
last_updated: 2025-04-24
entry_count: 6
---

# API Integration — Bug Catalog

## Authentication

### [Auth] API returns 401 despite valid credentials (2025-04-18)
- **Symptom:** API calls fail with 401 Unauthorized. Credentials verified correct in the dashboard.
- **Root cause:** Workflow platform places credentials in JSON body using `$credentials.apiKey` expression. Expression evaluates in headers but renders as literal string in body fields.
- **Fix:** Moved authentication from body to headers where credential interpolation works. Added request logging to verify credential resolution.
- **Key insight:** Always verify credential expression resolution with logging, especially in new field contexts.
- **Pattern:** P11 (Credential Expression Scope Limitation)

### [Auth] Token refresh fails silently (2025-03-25)
- **Symptom:** API calls work for 1 hour then fail. Manually restarting the service fixes it.
- **Root cause:** OAuth token refresh endpoint returns a success status with an error body when the refresh token is expired. Client checks status code (200) but doesn't check body for error indicators.
- **Fix:** Added body-level error checking before treating response as successful. Added refresh token rotation.
- **Key insight:** HTTP 200 doesn't mean success. Always check the response body for error indicators before extracting data.
- **Pattern:** P13 (Parse Code Matches Errors as Success)

## Data Sync

### [Sync] XML-RPC calls return malformed data (2025-04-12)
- **Symptom:** Integration with legacy system fails. API returns "malformed XML" errors.
- **Root cause:** Workflow automation platform's expression engine tries to evaluate `<?xml ...` as a template expression, corrupting the XML body.
- **Fix:** Switched to JSON-RPC endpoint (same API, different format). For endpoints that only support XML, used base64-encoded body with pre-request decode step.
- **Key insight:** Workflow automation expression engines assume JSON. Non-JSON bodies (XML, YAML) will be corrupted.
- **Pattern:** P12 (Expression Engine Corrupts Non-JSON Bodies)

### [Sync] Webhook processes events but data is stale (2025-04-05)
- **Symptom:** Webhook handler processes events successfully but the data in the database is outdated.
- **Root cause:** Two systems write to the same database table — the webhook handler and a background sync job. Background sync runs every 5 minutes and overwrites webhook updates with older data.
- **Fix:** Added `updated_at` timestamp check — background sync skips rows updated more recently than the sync source data. Designated webhook as authoritative for real-time updates.
- **Key insight:** Two writers to the same data = one will overwrite the other. Designate a single authoritative source, or use timestamp-based conflict resolution.
- **Pattern:** P02 (Multiple Write Sources → Data Corruption)

## Rate Limiting

### [Rate] Burst of 429 errors after dependency update (2025-03-18)
- **Symptom:** API integration suddenly hits rate limits. No change in traffic volume.
- **Root cause:** Updated the HTTP client library. New version removed default request coalescing, so duplicate requests that were previously deduplicated now all fire individually.
- **Fix:** Pinned HTTP client to previous version. Added explicit request deduplication in the calling code.
- **Key insight:** Dependency updates can change internal behaviors (caching, coalescing, retry logic) that affect external API usage. Check lock file diffs for any behavioral library changes.
- **Pattern:** P06 (Dependency Resolution Cascade)

## Error Handling

### [Error] Monitoring shows 100% success rate but users report failures (2025-04-20)
- **Symptom:** Dashboard shows all green. Users report the feature doesn't work.
- **Root cause:** Monitoring extracts "status" from response using regex `/\d+/`. Error response contains `{"error_code": 422, "message": "..."}`. Regex matches `422` but the monitoring categorizes any 3-digit number as a valid response code, and `422` passes the "is valid HTTP status" check.
- **Fix:** Changed monitoring to check `response.ok` (boolean) first, then extract status only from confirmed success responses. Added separate error tracking for non-2xx responses.
- **Key insight:** Extraction logic that works on success responses may also "work" on error responses — matching error data as valid data. Always check for errors FIRST.
- **Pattern:** P13 (Parse Code Matches Errors as Success)
