# Domain Catalogs — Organizing Bugs by Subsystem

## What Are Domain Catalogs?

Domain catalogs are collections of bug trajectories organized by subsystem — not by date. When debugging a payment processing issue, you search the payment catalog, not a chronological log of all bugs.

## Why Domain-Based Organization?

### Chronological Logs Fail At Scale

A flat log of all bugs:
```
2025-04-24: Fixed API timeout
2025-04-23: Fixed voice pipeline echo
2025-04-22: Fixed config sync issue
2025-04-21: Fixed API rate limiting
2025-04-20: Fixed voice pipeline delay
```

To find relevant history for a voice pipeline bug, you scan every entry. At 100+ entries, this is unusable.

### Domain Catalogs Scale

Organized by subsystem:
```
voice-pipeline/catalog.md     → 25 voice-specific bugs
api-integration/catalog.md    → 18 API-specific bugs
config-management/catalog.md  → 12 config-specific bugs
```

To find relevant history for a voice pipeline bug, you read one file.

## Creating a Domain Catalog

### Step 1: Identify Your Domains

Domains map to the major subsystems in your project. Common examples:

- **voice-pipeline** — Real-time audio, TTS, STT, VAD
- **api-integration** — Third-party API calls, webhooks, authentication
- **config-management** — Multi-source config, environment variables, feature flags
- **workflow-automation** — Background jobs, event processing, orchestration
- **database** — Queries, migrations, connection management
- **authentication** — Login, sessions, tokens, permissions
- **deployment** — CI/CD, containers, infrastructure
- **frontend** — UI rendering, state management, client-side errors

Start with 2-3 domains where you fix the most bugs. Add more as needed.

### Step 2: Create the Catalog File

```markdown
---
domain: voice-pipeline
description: Real-time audio processing, TTS, STT, and voice agent logic
last_updated: 2025-04-24
entry_count: 0
---

# Voice Pipeline — Bug Catalog

Entries organized by category within the domain. Each entry follows the 
standard trajectory format.

## TTS (Text-to-Speech)

(entries go here)

## STT (Speech-to-Text)

(entries go here)

## Flow Logic

(entries go here)

## Audio Processing

(entries go here)
```

### Step 3: Add Entries After Every Fix

Use the recording format from the debug trajectory protocol:

```markdown
### [TTS] Audio sounds metallic after format conversion (2025-04-15)
- **Symptom:** Output audio has harsh, tinny quality after sample rate conversion
- **Root cause:** Low-order FIR filter (~40dB stopband) causes aliasing 
  during 24kHz→8kHz downsampling
- **Fix:** Replaced hand-rolled resampler with professional audio library 
  (SoX-quality resampler, ~90dB stopband). File: audio_processor.py:128
- **Key insight:** Never hand-roll audio DSP when professional libraries exist. 
  The quality difference is audible and the performance is better.
- **Pattern:** New — candidate for "P20: DIY vs. Library Quality Gap"
```

## Cross-Referencing

### Within a Domain

If two bugs in the same catalog share a root cause, link them:

```markdown
- **Related:** See "[TTS] Duplicate audio frames" above — same pipeline stage
```

### Across Domains

If a bug in one domain caused symptoms in another:

```markdown
- **Related:** Root cause was config issue — see config-management catalog, 
  "[Resolution] Provider field mismatch (2025-04-10)"
```

### To Pattern Bank

Always link to the pattern:

```markdown
- **Pattern:** P10 (Contradictory Multi-Source Config)
```

## Catalog Maintenance

### When to Add
After every bug fix (Step 7 of the trajectory protocol). Even "trivial" bugs — patterns emerge from volume.

### When to Update
When a fix is later found to be incomplete:
```markdown
- **Update (2025-05-01):** Original fix was insufficient — also needed to 
  update the fallback chain. See entry below.
```

### When to Remove
When the code a bug refers to has been deleted. But check if the KEY INSIGHT still applies — the specific bug may be gone, but the lesson might transfer.

### When to Promote
When 3+ entries share a root cause type that isn't in the pattern bank yet, extract a new pattern (P20+).

## Measuring Value

Your domain catalogs are working well when:
- Pattern check (Step 1) finds a match more than 50% of the time
- Average debug time decreases over months
- You rarely need all 7 steps — most bugs resolve at Step 1 (pattern match)
- New team members debug faster by reading the catalogs
