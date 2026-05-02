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

## Debugger Strategy

When an agent has access to a runtime debugger (PDB, JDB, or equivalent), use these targeted investigation steps instead of blind stepping.

**Breakpoints:**
- Every config read call for the affected key (e.g., `settings.get("greeting")`, `os.environ.get("DATABASE_URL")`, `db.query("SELECT greeting FROM project_settings")`) — Whichever fires first wins

**Watch Expressions:**
- `config_value` at the point it is assigned — See the actual value the runtime uses, not what you expect
- `inspect.stack()` — At the config read breakpoint, identify which loader/module is providing the value
- `config.py:GREETING` — If this is never hit during a full request cycle, it is dead code

**Isolation Technique:**
Set breakpoints on ALL candidate config read sites for the same key. Run one full request. Only the breakpoint that fires is the active source. If `config.py` is never hit but `project_settings.greeting` DB read fires, the file-based constant is confirmed dead. Delete it and verify behavior is unchanged.

**Expected Evidence:**
Confirms pattern: the breakpoint on `config.py` never triggers during a real request, while a DB or environment read breakpoint does trigger and returns the live value. Rules it out: the `config.py` breakpoint fires — the constant is active, meaning the problem is a different value there, not a dead source.

## Related Patterns

- **P08** — Config chain gaps are about missing links; stale config is about dead links
- **P10** — Contradictory config often involves one stale source and one active source
