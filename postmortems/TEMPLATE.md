---
id: PMXX
name: Postmortem Title
date: YYYY-MM-DD
duration: Xh Ym
severity: SEV-1 | SEV-2 | SEV-3
patterns: [PXX, PYY]
---

# PMXX: Postmortem Title

## Summary

One paragraph: what happened, user-facing impact, duration, and how it was resolved.

## Timeline

All times in UTC.

| Time | Event |
|------|-------|
| HH:MM | Triggering event (deployment, config change, traffic spike) |
| HH:MM | First observable symptom |
| HH:MM | Detection (how: alert, user report, engineer noticed) |
| HH:MM | Investigation begins |
| HH:MM | First false lead pursued |
| HH:MM | Root cause identified |
| HH:MM | Fix applied |
| HH:MM | Service restored |
| HH:MM | All-clear confirmed |

## Detection

How was the incident discovered? How long between the trigger and detection?

What monitoring existed? What monitoring SHOULD have existed?

## Root Cause

Technical root cause, traced to its deepest layer. Reference applicable patterns from `patterns/`.

## False Leads

### False Lead 1: Title
- **Time spent:** X minutes
- **What was checked:** Specific investigation steps
- **Why it was ruled out:** Evidence that disproved this hypothesis
- **Lesson:** What would have ruled this out faster

### False Lead 2: Title
- **Time spent:** ...
- **What was checked:** ...
- **Why it was ruled out:** ...
- **Lesson:** ...

## Resolution

The fix applied under pressure. This is often not the ideal fix — it's the fix that restores service fastest.

## Blast Radius

### Direct Impact
- Users affected, requests failed, data lost

### Indirect Impact
- Downstream systems affected
- Data inconsistencies introduced
- Trust/reputation impact

### Near Misses
- What COULD have broken but didn't, and why

## What Went Well

Decisions, automation, or design choices that limited the damage.

## What Went Poorly

Decisions, gaps, or human factors that extended the incident. Be specific and blameless.

## Systemic Mitigation

Changes to prevent this CLASS of incident:

| Action | Prevents | Owner | Status |
|--------|----------|-------|--------|
| Description of change | What class of failure it prevents | Team/person | Done / In progress / Planned |

## Patterns

Which Debug Bank patterns apply and how they manifested in this incident.
