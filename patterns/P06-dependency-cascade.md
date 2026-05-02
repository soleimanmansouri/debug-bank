---
id: P06
name: Dependency Resolution Cascade
category: dependencies
severity: high
frequency: occasional
---

# P06: Dependency Resolution Cascade

## Pattern

Adding or updating a seemingly unrelated dependency triggers a transitive dependency upgrade with breaking changes. The direct dependency works fine, but a library deep in the dependency tree changes behavior.

## Check List (30-Second Diagnosis)

- [ ] Did the bug appear immediately after adding/updating a package?
- [ ] Is the breaking behavior in a library you didn't directly change?
- [ ] Does reverting the new package (and its lock file changes) fix the bug?

If 2+ checks are "yes," this pattern likely matches.

## Examples

### Example 1: WebRTC Extra Upgrades SDK
**Setup:** Adding a `webrtc` extra to a voice processing library. The extra has a dependency on a speech SDK.
**Symptom:** Speech-to-text produces garbled output after adding the webrtc feature.
**Root cause:** The webrtc extra pulled in speech-sdk v5, which changed the audio format. Previous lock file had v4.
**Fix:** Pin the speech SDK version in requirements: `speech-sdk>=4.0,<5.0`.

### Example 2: Test Framework Upgrades Serializer
**Setup:** Updating pytest from 7.x to 8.x.
**Symptom:** JSON fixtures fail to load — keys are in different order.
**Root cause:** pytest 8.x pulled in a new version of a JSON library that doesn't preserve insertion order.
**Fix:** Pin the JSON library version. Update fixtures to use order-independent comparison.

## Fix Strategy

1. Diff the lock file (before vs. after) to find ALL version changes
2. Identify which transitive dependency changed
3. Pin the critical transitive dependency to the known-good version
4. Test thoroughly — transitive changes can affect multiple subsystems

## Prevention

- Always review lock file diffs, not just direct dependency changes
- Pin critical dependencies explicitly, even if they're transitive
- Use dependency scanning tools to flag unexpected version jumps
- Test after every dependency change, even "unrelated" ones

## Debugger Strategy

When an agent has access to a runtime debugger (PDB, JDB, or equivalent), use these targeted investigation steps instead of blind stepping.

**Breakpoints:**
- The first call into the suspected transitive dependency (e.g., `speech_sdk.transcribe()` or the JSON serializer's `loads()`) — Step into the library code to see which version's implementation runs

**Watch Expressions:**
- `speech_sdk.__version__` (or `importlib.metadata.version("speech-sdk")`) — Compare against the expected pinned version
- `audio_format` or the key parameter whose behavior changed — See what value the new library version receives vs. what it expects
- `sys.modules["speech_sdk"].__file__` — Confirms which installed copy is actually loaded

**Isolation Technique:**
At the transitive dependency entry point, evaluate `module.__version__` in the debugger REPL. If it differs from the version in the last known-good lock file, step through the library's changed code path to identify what behavior shifted. Then set `sys.modules` aside and import the pinned version directly to confirm the bug disappears.

**Expected Evidence:**
Confirms pattern: runtime `__version__` of the transitive package differs from the lock file's pinned version, and stepping into that package reveals a changed code path (different default, different format, removed parameter). Rules it out: all transitive dependency versions match the lock file — points to a logic change in your own code instead.

## Related Patterns

- **P01** — Dependency updates can change parent class defaults
