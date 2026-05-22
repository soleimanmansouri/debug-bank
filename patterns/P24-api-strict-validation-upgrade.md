---
id: P24
name: API Strict Validation Upgrade
category: platform-quirks
severity: critical
frequency: occasional
---

# P24: API Strict Validation Upgrade

## Pattern

A third-party API silently accepted invalid or unsupported parameters, then a server-side update enforces strict validation. Code that worked for weeks/months breaks instantly on the next deployment (or connection reset) without any local code change. Persistent connections (WebSockets, gRPC streams) mask the change until the process restarts.

## Check List (30-Second Diagnosis)

- [ ] Did the code work yesterday without any local changes?
- [ ] Does the error message mention "not supported" or "invalid parameter"?
- [ ] Is the failing parameter one you never explicitly tested, but it "always worked"?
- [ ] Did a deploy/restart happen right before the failure started?

If 3+ checks are "yes," this pattern likely matches.

## Examples

### Example 1: Gemini Live Rejects Penalty Params
**Setup:** Pipecat voice pipeline passed `frequency_penalty=0.4` and `presence_penalty=0.2` in `InputParams` to `GeminiLiveLLMService`. These are OpenAI-style generation parameters. Gemini Live silently ignored them for months.
**Symptom:** After a routine deploy, ALL voice agents went silent. Callers heard nothing for 60s until a watchdog killed the call. Error: `1007 None. frequency_penalty not supported in generation config`. Zero turns, empty transcripts across all dealers.
**Root cause:** Google updated Gemini Live API to strictly validate generation config. The deploy restarted the Fly.io machine, forcing new WebSocket connections to Gemini. New connections hit the strict validator; old connections (pre-deploy) were grandfathered under lenient rules.
**Fix:** Removed both `frequency_penalty` and `presence_penalty` from `InputParams` in `base.py`. Required two deploys because the first fix only removed one of the two rejected params.

### Example 2: Gemini Live Rejects max_output_tokens
**Setup:** Same pipeline previously passed `max_tokens` (mapped to `max_output_tokens`) to Gemini Live.
**Symptom:** Same 1007 WebSocket error, same silent calls.
**Root cause:** Same pattern: Gemini Live doesn't support `max_output_tokens` in generation config. Was caught earlier and set to `None` with a comment, but the penalty params were missed.
**Fix:** Set `max_tokens=None` with comment: "Live API rejects max_output_tokens".

## Fix Strategy

1. Read the exact error message: it names the rejected parameter
2. **Audit ALL sibling parameters** in the same config block, not just the one named in the error
3. Cross-reference against the API's official documentation for supported parameters
4. Remove or conditionally exclude unsupported params
5. Deploy and verify no new 1007/validation errors appear
6. Check if any other services (STT, TTS) have similar param leakage

## Prevention

- Only pass parameters explicitly listed in the target API's documentation
- When wrapping one API's params (OpenAI-style) for another (Gemini), maintain an explicit allowlist
- Add a startup self-test that validates config against the API before accepting live traffic
- Subscribe to API changelog/deprecation notices for critical dependencies
- After fixing one rejected param, grep for ALL params from the same family

## Debugger Strategy

**Breakpoints:**
- The WebSocket connect/handshake method (e.g., `_connect` in the LLM service) — inspect the config payload being sent

**Watch Expressions:**
- `generation_config` or `params` dict at the point of serialization — list every key being sent
- WebSocket close frame reason/code — 1007 = invalid payload data

**Isolation Technique:**
Strip the config to minimum (only `temperature`) and add params back one at a time. The connection that fails identifies the rejected param.

**Expected Evidence:**
- **This pattern:** WebSocket connects, immediately receives 1007 close frame with "not supported" message. No audio generated.
- **Not this pattern:** Connection succeeds, audio streams, error happens mid-conversation.

## Related Patterns

- **P07** (Stale Config) — Config exists but isn't read; here config IS read but shouldn't be sent
- **P22** (Iterative Fix Regression) — First fix incomplete, second error surfaces. Always audit the full parameter set.
