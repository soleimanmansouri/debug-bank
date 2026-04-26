---
domain: voice-pipeline
description: Real-time voice AI systems — TTS, STT, audio processing, conversation flow, and telephony integration
last_updated: 2025-04-24
entry_count: 8
---

# Voice Pipeline — Bug Catalog

## TTS (Text-to-Speech)

### [TTS] Audio sounds metallic after sample rate conversion (2025-04-15)
- **Symptom:** Output audio has harsh, tinny quality. Users report "robot voice."
- **Root cause:** Low-order FIR filter (~40dB stopband attenuation) used for 24kHz→8kHz downsampling causes aliasing artifacts.
- **Fix:** Replaced hand-rolled resampler with professional audio library (SoX-quality resampler, ~90dB stopband). `audio_processor.py:128`
- **Key insight:** Never hand-roll audio DSP when professional libraries exist. The quality gap is audible and the performance is equal or better.
- **Pattern:** New — candidate for "P20: DIY vs. Library Quality Gap"

### [TTS] Every response spoken twice (2025-03-12)
- **Symptom:** Users hear each TTS response duplicated — "Hello how can I help? Hello how can I help?"
- **Root cause:** Caching wrapper inherits `auto_push_output=True` from parent class. Cache pushes frames AND parent pushes frames.
- **Fix:** Set `super().__init__(auto_push_output=False)` in the caching wrapper.
- **Key insight:** When wrapping pipeline services, audit ALL parent defaults. Duplication = two components doing the same job.
- **Pattern:** P01 (Wrapper/Decorator Default Mismatch)

### [TTS] Greeting takes 6-8 seconds to play (2025-04-10)
- **Symptom:** Callers hear 6-8 seconds of silence before the agent greeting. Many hang up.
- **Root cause:** Voice model has ~3.5s fixed time-to-first-byte. Combined with prompt processing, greeting latency is unacceptable.
- **Fix:** Pre-render greeting audio via a fast TTS model at startup. Play cached audio immediately on call connect. Pipeline takes over after greeting.
- **Key insight:** For latency-critical audio (greetings), pre-render and cache. Don't rely on real-time generation for the first impression.
- **Pattern:** New — "P21: First-Impression Latency" candidate

## STT (Speech-to-Text)

### [STT] Wrong language detected for bilingual callers (2025-03-28)
- **Symptom:** STT model switches to English mid-conversation when caller uses an English loanword.
- **Root cause:** Auto-language-detection resets per utterance. A single English word triggers language switch.
- **Fix:** Pin the STT language to the expected primary language. Disable auto-detection.
- **Key insight:** Auto-detection is unreliable for languages with heavy loanword usage. Pin the language explicitly.
- **Pattern:** P05 (Context-Dependent Flag Duality) — auto-detect is good for unknown callers, bad for known-language contexts

## Flow Logic

### [Flow] Agent skips appointment confirmation step (2025-03-20)
- **Symptom:** Agent collects appointment details but books without asking for confirmation.
- **Root cause:** LLM sees example confirmation dialogue in system prompt and treats it as already completed.
- **Fix:** Removed example dialogue. Added explicit flow node that requires confirmation before booking.
- **Key insight:** LLMs treat example dialogues as completed interactions. Use flow-level enforcement for critical steps, not prompt examples.
- **Pattern:** P04 (LLM Copies Example Text as Behavior)

### [Flow] Agent enters farewell loop after call end (2025-04-08)
- **Symptom:** After user says goodbye, agent repeats "Goodbye, have a great day! ... Take care! ... Bye!" for 10+ seconds.
- **Root cause:** No pipeline termination after end-of-conversation tool call. Model fills silence with more output. Generous 15s timeout allows long loops.
- **Fix:** Set timeout to `speech_duration + 1s`. Added idempotency guard on `end_conversation` handler. First call triggers disconnect, subsequent calls are no-ops.
- **Key insight:** Voice models fill silence. Always set tight timeouts and terminate the pipeline explicitly after conversation-ending events.
- **Pattern:** P18 (Model Loops Without Stop Signal)

## Telephony

### [Telephony] Transfer connects to wrong department (2025-04-02)
- **Symptom:** Caller asks for service department but gets connected to sales.
- **Root cause:** Department phone numbers resolved through fallback chain: API → database → YAML → hardcoded. Database entry missing for service department, falling through to YAML with outdated numbers.
- **Fix:** Populated database with current department numbers. Added monitoring alert when fallback to YAML occurs.
- **Key insight:** Multi-source config fallback chains fail silently. Always log when a lower-priority source is used.
- **Pattern:** P08 (Config Resolution Chain Gap)

### [Telephony] Calls fail with "invalid call markup" after provider migration (2025-03-15)
- **Symptom:** All outbound calls fail. Telephony provider returns "invalid markup" error.
- **Root cause:** Provider config updated to new provider but the call markup generator still uses old provider's format. Provider field says "provider_b" but sibling `markup_format` field still says "provider_a_format".
- **Fix:** Updated all sibling config fields to match new provider. Added validation that checks provider + format compatibility at startup.
- **Key insight:** When migrating providers, change ALL config fields — not just the provider selector.
- **Pattern:** P10 (Contradictory Multi-Source Config)
