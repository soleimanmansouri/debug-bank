---
id: P10
name: Contradictory Multi-Source Config
category: configuration
severity: high
frequency: common
---

# P10: Contradictory Multi-Source Config

## Pattern

A configuration object has a provider/type selector field that points to one system, but sibling parameter fields belong to a different system. The selector and parameters are internally inconsistent.

## Check List (30-Second Diagnosis)

- [ ] Does the config have a "provider," "type," or "engine" field that selects a system?
- [ ] Do sibling fields (IDs, keys, URLs) belong to a DIFFERENT system than the selector?
- [ ] Was there a recent provider migration or config change?

If 2+ checks are "yes," this pattern likely matches.

## Examples

### Example 1: TTS Provider Mismatch
**Setup:** Config has `tts_provider: "provider_a"` but `voice_id: "id-from-provider-b"`.
**Symptom:** TTS fails with "voice not found" error, or silently uses a default voice.
**Root cause:** Provider was switched from B to A, but the voice ID wasn't updated.
**Fix:** Update `voice_id` to a valid ID from provider A. Add validation that checks sibling field compatibility.

### Example 2: Database Connection Mismatch
**Setup:** Config has `db_type: "postgres"` but `connection_string: "mongodb://..."`.
**Symptom:** Connection fails with cryptic protocol error.
**Root cause:** Database was migrated from MongoDB to Postgres, but connection string wasn't updated.
**Fix:** Update connection string. Add startup validation that checks URL scheme matches db_type.

## Fix Strategy

1. Identify the selector field (provider, type, engine)
2. List ALL sibling fields that depend on the selector
3. Verify each sibling field is valid for the selected provider
4. Add startup/load-time validation that checks consistency

## Prevention

- When changing a provider selector, always update ALL sibling fields
- Add validation that cross-checks selector and parameter compatibility
- Use typed config objects that enforce provider-specific field sets

## Debugger Strategy

When an agent has access to a runtime debugger (PDB, JDB, or equivalent), use these targeted investigation steps instead of blind stepping.

**Breakpoints:**
- `config.load` / config deserialization entry point — inspect the full config object immediately after it is parsed
- `provider_init` / the constructor that uses the selector field to initialize the backend

**Watch Expressions:**
- `config.tts_provider` (or equivalent selector) — what system is selected?
- `config.voice_id` / `config.connection_string` — do these values belong to the selected provider?
- `type(config.voice_id)` — a UUID vs a name format can reveal which provider the value came from

**Isolation Technique:**
At the config load breakpoint, dump the selector field and all sibling fields side-by-side. Cross-reference the voice ID / connection string format against known provider patterns (e.g., ElevenLabs IDs are 20-char alphanumeric; MongoDB URIs start with `mongodb://`).

**Expected Evidence:**
Confirms: selector says provider A, but a sibling field contains an ID/URL that only exists in provider B. Rules out: all sibling fields are valid for the selected provider.

## Related Patterns

- **P07** — Stale config can leave behind parameters from a previous provider
- **P08** — Config chain gaps can cause different fields to resolve from different sources
