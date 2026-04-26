---
domain: config-management
description: Multi-source configuration, environment variables, feature flags, and deployment settings
last_updated: 2025-04-24
entry_count: 6
---

# Config Management — Bug Catalog

## Multi-Source Resolution

### [Resolution] Feature uses wrong provider after migration (2025-04-10)
- **Symptom:** TTS output uses old provider's voice despite migration to new provider.
- **Root cause:** Config has `tts_provider: "new_provider"` but `voice_id: "old-provider-voice-id-123"`. Provider selector updated, sibling parameters not updated.
- **Fix:** Updated all provider-dependent parameters. Added startup validation that cross-checks provider selector with parameter formats (each provider has a distinct ID format).
- **Key insight:** Provider migration requires updating ALL sibling fields, not just the selector. Add cross-validation.
- **Pattern:** P10 (Contradictory Multi-Source Config)

### [Resolution] Config change has no effect (2025-03-22)
- **Symptom:** Changed `greeting_message` in the config file. Greeting didn't change.
- **Root cause:** Runtime reads greeting from database, not config file. Config file value is dead code — was the original source but database was added later and takes priority.
- **Fix:** Updated the database value. Removed the dead config entry. Added comment in config documenting which values are actually read from DB.
- **Key insight:** When a config change has no effect, trace where the runtime ACTUALLY reads from. Don't assume the obvious source is the active one.
- **Pattern:** P07 (Stale/Dead Config)

### [Resolution] Some users see feature, others don't (2025-04-08)
- **Symptom:** Feature flag is "enabled" but only some users see the feature.
- **Root cause:** Flag resolution chain: user_override → experiment → org_default → global_default. Some users have stale `user_override=false` from a previous A/B test. Global is `true` but user overrides take priority.
- **Fix:** Cleaned up stale user overrides from the previous experiment. Added an admin tool to view the full resolution chain per user.
- **Key insight:** Multi-level flag resolution means the global value might not be what users experience. Always check the full chain.
- **Pattern:** P08 (Config Resolution Chain Gap)

## Environment Variables

### [Env] Application works locally but fails in staging (2025-03-30)
- **Symptom:** All API integrations fail in staging. Work perfectly in local development.
- **Root cause:** Local `.env` file has `API_BASE_URL=https://api.example.com`. Staging environment has `API_BASE_URL` set by the deployment platform, but the value includes a trailing slash. Client code concatenates `base_url + "/endpoint"` producing a double-slash URL.
- **Fix:** Added URL normalization to strip trailing slashes from base URLs. Added integration test that validates URL construction.
- **Key insight:** Environment variables from different sources may have different formatting (trailing slashes, quotes, whitespace). Always normalize.
- **Pattern:** New — candidate for "P22: Environment Format Divergence"

## Deployment Config

### [Deploy] Build succeeds but app crashes on startup (2025-04-14)
- **Symptom:** CI build passes all tests. Deployed app crashes immediately with missing module error.
- **Root cause:** A new dependency was added to `requirements.txt` but not to the Docker build's `requirements.txt` (separate file for container builds). CI uses the project file, Docker uses the container file.
- **Fix:** Unified to a single requirements file. Docker build now uses the same file as CI.
- **Key insight:** Multiple dependency manifests = guaranteed drift. Unify to a single source or add CI validation that all manifests match.
- **Pattern:** P02 (Multiple Write Sources → Data Corruption) — variant: multiple config sources for the same purpose

### [Deploy] Automated config update corrupts system prompt (2025-04-01)
- **Symptom:** System prompt suddenly contains a paragraph of review notes instead of instructions.
- **Root cause:** Automated feedback pipeline reads change request descriptions and writes them to config fields. A CR description was mapped to the `system_prompt` field because the field name matched a keyword in the automation rules.
- **Fix:** Added structural validation on the automation pipeline — system prompts must meet minimum length (200 chars) and contain required sections. Rejected payloads that look like free-text descriptions.
- **Key insight:** Automated pipelines that write free-text to structured fields will eventually corrupt data. Always validate the payload structure matches the target field.
- **Pattern:** P09 (Auto-Apply Pipeline Writing Feedback as Data)
