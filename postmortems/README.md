# Postmortems — Learning From Production Incidents

Anonymized postmortem reports from real production incidents. Each follows a consistent structure that goes beyond "what broke" to cover blast radius, systemic mitigation, and what almost broke but didn't.

## Why Postmortems

Patterns tell you WHAT can go wrong. Postmortems tell you what it LOOKS LIKE when it does — the timeline, the false leads, the human decisions that made it better or worse, and the systemic changes that prevent recurrence.

Senior engineers learn more from reading 10 good postmortems than from fixing 100 isolated bugs.

## Structure

Every postmortem includes:

| Section | Purpose |
|---------|---------|
| **Summary** | One paragraph: what happened, impact, duration |
| **Timeline** | Minute-by-minute from trigger to resolution |
| **Detection** | How the incident was discovered (monitoring, user report, accident) |
| **Root Cause** | The technical cause, traced to its deepest layer |
| **False Leads** | What was investigated and ruled out, and how long each cost |
| **Resolution** | The fix applied under pressure to restore service |
| **Blast Radius** | What else was affected, including non-obvious downstream effects |
| **What Went Well** | Decisions or systems that limited the damage |
| **What Went Poorly** | Decisions or gaps that extended the damage |
| **Systemic Mitigation** | Changes to prevent this CLASS of incident, not just this specific one |
| **Patterns** | Which Debug Bank patterns apply |

## Postmortem Index

| # | Title | Duration | Impact | Patterns |
|---|-------|----------|--------|----------|
| PM01 | [The Invisible Throttle](PM01-invisible-throttle.md) | 4.5 hours | 12% of API requests silently degraded | P07 + P13 |
| PM02 | [Midnight Migration](PM02-midnight-migration.md) | 2 hours | Full outage, 30 minutes of data loss | P02 + P08 |
| PM03 | [The Helpful Retry](PM03-helpful-retry.md) | 35 minutes | Payment duplications, $23K in erroneous charges | P06 + P03 |

## Writing Your Own

Use `TEMPLATE.md`. The hardest section to write well is **What Went Poorly** — be honest about human decisions, not just technical failures. The most valuable section is **Systemic Mitigation** — the fix for this incident is less important than the fix for this class of incidents.
