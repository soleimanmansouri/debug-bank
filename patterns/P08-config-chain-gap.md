---
id: P08
name: Config Resolution Chain Gap
category: configuration
severity: high
frequency: common
---

# P08: Config Resolution Chain Gap

## Pattern

Configuration is resolved through a fallback chain (e.g., database → JSON file → YAML file → hardcoded default). A missing link in the chain causes silent fallback to stale or incorrect data further down.

## Check List (30-Second Diagnosis)

- [ ] Does the system use multiple config sources with fallback priority?
- [ ] Is the bug caused by the system using a value from the wrong source?
- [ ] Is there a config source in the chain that should have the value but doesn't?

If 2+ checks are "yes," this pattern likely matches.

## Examples

### Example 1: Transfer Routing Falls Through
**Setup:** Transfer numbers resolved via: API response → database table → YAML config → hardcoded fallback.
**Symptom:** Calls transfer to the wrong department number.
**Root cause:** Database table is empty for this department. System falls through to YAML which has an outdated number.
**Fix:** Populate the database table with current numbers. Add monitoring for empty DB entries.

### Example 2: Feature Flag Resolution
**Setup:** Feature flags resolved via: user override → experiment → team default → global default.
**Symptom:** A user sees a feature that should be disabled for them.
**Root cause:** User override entry was deleted during a migration. System falls through to experiment, which has the feature enabled.
**Fix:** Restore the user override. Add a check that warns when expected override entries are missing.

## Fix Strategy

1. Map the complete fallback chain (every source, in order)
2. Check each source — which one is actually providing the value?
3. Populate the missing link, or fix the source that should be authoritative
4. Add monitoring/logging for fallback events (when a higher-priority source is empty)

## Prevention

- Document the fallback chain explicitly (which source, in what order)
- Log when fallback occurs — "Using YAML fallback for department X, DB entry missing"
- Validate that the primary source is populated for all expected keys

## Related Patterns

- **P07** — Stale config is a dead source; chain gap is a missing source
- **P10** — Contradictory config often involves different chain resolutions per field
