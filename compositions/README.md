# Compositions — When Patterns Combine

Real production bugs rarely match a single pattern. They combine two or three patterns into a failure mode that's harder to diagnose than either pattern alone. Compositions document these common combinations: which patterns pair together, why they amplify each other, and how to detect the combination early.

## Why Compositions Matter

Single-pattern bugs are straightforward: you match the pattern, apply the fix. Composed bugs are harder because:

- The symptom matches Pattern A, but the fix for Pattern A doesn't work
- Pattern B is hidden behind Pattern A's symptoms
- The root cause only exists because both patterns are active simultaneously
- Fixing only one pattern shifts the symptom but doesn't resolve the bug

## How to Use

When investigating a bug:

1. Match against individual patterns first (as usual)
2. If the pattern match "almost" fits but the fix doesn't work, check compositions
3. Look for a second pattern hiding behind the first

## Composition Index

| ID | Composition | Patterns | Signal |
|----|------------|----------|--------|
| C01 | [Write Race + Stale Fallback](C01-write-race-stale-fallback.md) | P02 + P08 | Intermittent stale data that self-heals on a timer then re-breaks |
| C02 | [Upgrade Cascade + Retry Multiplier](C02-upgrade-cascade-retry-multiplier.md) | P06 + P03 | Traffic amplification after a "minor" dependency update |
| C03 | [Silent Success + Stale Config](C03-silent-success-stale-config.md) | P13 + P07 | Feature appears to work but produces wrong results, no errors |
| C04 | [LLM Hallucination + Missing Stop Signal](C04-llm-hallucination-missing-stop.md) | P04 + P18 | AI agent produces confidently wrong output in an infinite loop |
| C05 | [Prompt Limits + Flag Duality](C05-prompt-limits-flag-duality.md) | P19 + P05 | Prompt engineering fixes one context but breaks another |
