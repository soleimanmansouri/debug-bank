# Scenarios — Multi-Service Debugging Challenges

Scenarios are self-contained, reproducible debugging environments that go beyond single-file bugs. Each scenario simulates a real production system with an injected fault that spans multiple services, files, or timing boundaries.

## Who This Is For

Senior and staff engineers who debug systems, not functions. If you're comfortable with single-file bugs and want to practice the harder kind — where the symptom is in service A, the cause is in service B, and the trigger is a timing issue in service C — these are for you.

## Difficulty Tiers

| Tier | Scope | Example |
|------|-------|---------|
| **L3** | Multi-service, single machine | Two services + shared database + message queue |
| **L4** | Distributed / timing-dependent | Race conditions, cache coherence, retry storms |

All scenarios in this directory are L3 or L4. For L1-L2 bugs, see `examples/`.

## How to Use

### With an AI Agent
Drop the scenario description into your agent's context. The agent should use the Debug Trajectory Protocol to investigate. Compare its approach and conclusion against the sealed solution.

### Solo Practice
1. Read the **Setup** and **Symptom** sections
2. Form your own hypotheses before reading further
3. Work through the investigation using the protocol
4. Compare against the **Root Cause** and **Solution** sections

## Scenario Index

| # | Name | Tier | Patterns | Key Challenge |
|---|------|------|----------|---------------|
| S01 | [Stale Cache Race](S01-stale-cache-race.md) | L4 | P02 + P08 | Cache invalidation arrives after consumer reads stale data |
| S02 | [Retry Storm Amplification](S02-retry-storm-amplification.md) | L4 | P06 + P03 | Library upgrade changes retry defaults, cascading across services |
| S03 | [Silent Schema Drift](S03-silent-schema-drift.md) | L3 | P07 + P02 + P13 | Migration runs on service A's DB but service B reads stale schema cache |

## Writing Your Own

Use `TEMPLATE.md` as a starting point. Good scenarios have:

- **Multiple investigation paths** — at least 2 plausible-but-wrong hypotheses
- **Cross-boundary root cause** — the fix isn't in the file where the symptom appears
- **Observable evidence** — each hypothesis can be confirmed or falsified with specific checks
- **Pattern composition** — the scenario should involve 2+ patterns from `patterns/`
