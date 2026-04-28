---
id: SXX
name: Scenario Name
tier: L3 | L4
patterns: [PXX, PYY]
services: [service-a, service-b, ...]
---

# SXX: Scenario Name

## System Architecture

Describe the services, how they communicate, and the data flow. Include a diagram if helpful:

```
[Service A] --HTTP--> [Service B] --writes--> [Database]
                                  --publishes--> [Queue] --consumed-by--> [Service C]
```

## Setup

What the system looks like before the bug. Include:
- Service versions and configurations
- Database schema (relevant tables/fields)
- Message formats and protocols
- Any recent changes that introduced the bug

## Symptom

What users or monitors observe. Be specific:
- Error messages (exact text)
- Metrics (latency, error rates, success rates)
- Timing (when does it happen? always, intermittently, under load?)
- What works vs. what's broken

## Red Herrings

List 2-3 plausible but incorrect hypotheses that an investigator might pursue:

### Red Herring 1: Title
- **Why it looks plausible:** What evidence points here
- **Why it's wrong:** What evidence rules it out
- **How to falsify:** Specific check that disproves this

### Red Herring 2: Title
- **Why it looks plausible:** ...
- **Why it's wrong:** ...
- **How to falsify:** ...

## Root Cause

The actual root cause. Explain:
- Which service contains the bug
- The exact mechanism (code path, timing, data flow)
- Why the symptom appears where it does (not where the cause is)
- Which patterns from `patterns/` apply and how they compose

## Investigation Path

The ideal debugging trajectory following the protocol:

1. **Pattern Check:** Which patterns should be considered and why
2. **Reproduce:** How to trigger the bug reliably
3. **Hypothesize:** The correct hypothesis ranking
4. **Isolate:** The binary search path that converges fastest
5. **Diagnose:** The call chain from trigger to symptom

## Solution

The minimal fix. Include:
- What to change and where
- Why this addresses the root cause (not a symptom)
- How to verify the fix works
- What monitoring to add to prevent recurrence

## Blast Radius

What else could break or could have broken:
- Adjacent systems affected by the same root cause
- Data that may have been corrupted during the incident window
- Downstream consumers that may have cached bad data

## Lessons

Generalizable takeaways for the pattern bank.
