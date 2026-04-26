---
id: P07
name: Stale/Dead Config
category: configuration
severity: medium
frequency: common
---

# P07: Stale/Dead Config

## Pattern

A configuration value exists (in a file, database, or environment variable) but is never actually read by the runtime. The real value comes from a different source. Changing the "obvious" config has no effect.

## Check List (30-Second Diagnosis)

- [ ] Did you change a config value but the behavior didn't change?
- [ ] Is there more than one place where this config could be defined?
- [ ] Can you find the exact line of code that reads this specific config source?

If check 1 is "yes" and check 3 is "no," this pattern likely matches.

## Examples

### Example 1: Constant Overridden by Database
**Setup:** A `GREETING` constant is defined in `config.py`. The runtime reads the greeting from a database table.
**Symptom:** Changing the constant has no effect on the greeting.
**Root cause:** The constant is dead code — real greeting comes from `project_settings.greeting` in the database.
**Fix:** Delete the dead constant. Update the database value instead.

### Example 2: Environment Variable Shadowed by Config File
**Setup:** `DATABASE_URL` is set in `.env` and also in `config/database.yml`. The app reads from `database.yml`.
**Symptom:** Changing `.env` doesn't change the database connection.
**Root cause:** Config file takes priority over environment variable in this framework.
**Fix:** Update `database.yml`, or change the loading order to prioritize env vars.

## Fix Strategy

1. Trace the code path from behavior to config read — find the EXACT source
2. Verify by changing the actual source (not the assumed one)
3. Delete or document the stale config to prevent future confusion

## Prevention

- When adding config, document where the runtime reads from
- Periodically audit config files for values that are never referenced in code
- Use a single config loading mechanism, not multiple overlapping ones

## Related Patterns

- **P08** — Config chain gaps are about missing links; stale config is about dead links
- **P10** — Contradictory config often involves one stale source and one active source
