# Feedback Rules — Behavioral Memory

## What Are Feedback Rules?

Feedback rules are persistent behavioral modifications captured from user corrections and confirmations. They're the mechanism by which an AI agent adapts to a specific user's working style over time.

Unlike factual memory ("the database is Postgres"), feedback rules change HOW the agent works ("always run tests autonomously, don't ask me to click buttons").

## Structure

Every feedback rule has three parts:

1. **The Rule** — What to do or not do (one clear sentence)
2. **Why** — The reason this matters (what incident or preference drives it)
3. **How to Apply** — When and where the rule activates (specific scope)

The `Why` is critical. Without it, the agent follows rules blindly and can't judge edge cases. With it, the agent can reason: "This rule exists because of X. In this situation, X doesn't apply, so the rule doesn't apply."

## Categories

### Workflow Rules
How the agent should structure its work.

Examples:
- Always enter plan mode before multi-file changes
- Run tests autonomously instead of asking user to verify
- End sessions with a structured summary table
- Never proceed with background work after asking a question — wait for response

### Tech Stack Rules
How to work with specific technologies in this project.

Examples:
- Never touch the legacy system unless explicitly asked
- Integration tests hit real databases, not mocks
- Always run linter before deploying to production
- Pin critical dependencies — check lock file after adding any package

### Environment Rules
How to interact with the development/deployment environment.

Examples:
- Development is always on localhost — never write to production URLs
- VM environments lose state per shell — always provide full command blocks
- Always show diffs before deploying to external services

### Safety Rules
What NOT to do, based on past incidents.

Examples:
- Never auto-merge feature branches — analyze first, wait for approval
- Never deploy to production during business hours without explicit approval
- Always filter test/internal data before presenting analytical reports

## Building Your Rule Set

### Starting From Zero

You won't have feedback rules on day one. They accumulate naturally:

1. Work normally with the agent
2. When the agent does something wrong, correct it
3. The agent captures the correction as a feedback rule
4. Next session, the rule is loaded and applied
5. Over time, corrections decrease as the agent adapts

### Critical Mass

After ~15-20 rules, you'll notice the agent rarely needs the same correction twice. After ~30+ rules, the agent's working style closely matches your preferences.

### Maintenance

- **Remove outdated rules** — If the codebase changed and a rule no longer applies, delete it
- **Merge similar rules** — If 3 rules say "be careful with config," merge into one specific rule
- **Update scope** — Rules created for one project may apply more broadly (or more narrowly) than originally written

## Anti-Patterns in Feedback Rules

| Anti-Pattern | Problem | Fix |
|---|---|---|
| "Be more careful" | Not actionable | Specify WHAT to be careful about |
| Rules without Why | Can't judge edge cases | Always include the incident/reason |
| Scope: "everywhere" | Over-applied, causes friction | Narrow to specific files/contexts |
| Duplicate rules | Confusion about which to follow | Merge into one authoritative rule |
| Rules from one-time incidents | Over-fitted to a past situation | Only persist if it could recur |

## Integration With Debugging

Feedback rules and debug patterns are complementary:

- **Patterns** = "This class of bug has this root cause"
- **Feedback rules** = "When you encounter this class of bug, approach it THIS way"

Example: Pattern P08 (Config Chain Gap) tells you what the bug IS. A feedback rule might say "Always trace the full config fallback chain before assuming a config value is correct — we wasted 3 hours last time assuming the DB value was right when it was falling through to a stale YAML file."

The pattern identifies the bug. The feedback rule prevents the investigation mistake.
