---
name: pattern-check
description: Quick pre-investigation scan of the pattern bank. Use before any debugging session to check if the current bug matches a known root cause pattern. Takes 30 seconds, saves hours.
version: 1.0.0
user-invocable: true
argument-hint: "[symptom description]"
---

# Pattern Check — Quick Scan

You are performing a pattern check before debugging. This is Step 1 of the debug trajectory protocol.

## Instructions

1. Read the symptom/error description provided
2. Scan each pattern (P01-P19+) in the pattern bank
3. For each pattern, check: "Could this symptom be caused by this root cause type?"
4. Report your findings

## Output Format

### If Match Found

```
PATTERN MATCH: P[XX] — [Pattern Name]

Confidence: HIGH / MEDIUM / LOW
Reasoning: [Why this pattern matches the symptom]

Suggested checks:
- [ ] [Check 1 from the pattern's check list]
- [ ] [Check 2]
- [ ] [Check 3]

If checks confirm, apply fix strategy from P[XX].
```

### If No Match

```
NO PATTERN MATCH

Closest patterns considered:
- P[XX]: [Why it was close but doesn't match]
- P[XX]: [Why it was close but doesn't match]

Proceed to Step 2 (Reproduce) of the debug trajectory protocol.
```

### If Multiple Matches

```
MULTIPLE PATTERN MATCHES (ranked by likelihood):

1. P[XX] — [Name] (CONFIDENCE: HIGH)
   Reasoning: [Why]
   
2. P[XX] — [Name] (CONFIDENCE: MEDIUM)
   Reasoning: [Why]

Start with the highest-confidence match. If its checks fail, try the next.
```

## Speed Requirement

This check should take under 60 seconds. Do not investigate, reproduce, or attempt fixes during a pattern check. Only scan and report.

The value of this step is SPEED — a 30-second check that saves hours of re-investigation. If you spend more than 60 seconds, you're over-investigating.
