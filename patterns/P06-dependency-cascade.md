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

## Related Patterns

- **P01** — Dependency updates can change parent class defaults
