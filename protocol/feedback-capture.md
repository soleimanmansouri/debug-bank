# Feedback Capture Protocol

## Purpose

When a user corrects the agent's approach, that correction should become a persistent, enforceable rule — not a one-time adjustment that's forgotten next session.

## Why This Matters

AI agents make the same mistakes repeatedly because corrections disappear when the context window resets. A user who says "don't mock the database" on Monday will need to say it again on Wednesday unless the correction is captured as a persistent rule.

Feedback capture closes this loop: correction → persistent rule → behavioral change → compound improvement.

## What to Capture

### Capture Corrections (Obvious)
User says: "No, don't do that" / "Stop doing X" / "That's wrong because..."

### Capture Confirmations (Subtle — Watch For These)
User says: "Yes, exactly" / "Perfect, keep doing that" / accepts an unusual choice without pushback.

**Why confirmations matter:** If you only capture corrections, the agent avoids past mistakes but drifts away from validated approaches. Record both what NOT to do and what TO do.

## Feedback Rule Format

```markdown
---
name: descriptive-rule-name
type: feedback
---
The rule itself — clear, actionable, one sentence if possible.

**Why:** The reason this rule exists. What went wrong, what incident this prevents, 
or what the user values. Include enough context to judge edge cases.

**How to apply:** When and where this rule activates. Be specific — 
"all test files" is better than "when testing."
```

## Examples

### From a Correction

User: "Don't mock the database in integration tests — we got burned last quarter when mocked tests passed but the prod migration failed."

```markdown
---
name: no-db-mocks-in-integration
type: feedback
---
Integration tests must hit a real database, not mocks.

**Why:** Prior incident where mock/prod divergence masked a broken migration.
Mocks only appropriate for unit tests of business logic.

**How to apply:** Any test file in `tests/integration/` or test functions 
tagged with `@integration`. Unit tests in `tests/unit/` may still use mocks.
```

### From a Confirmation

User: "Yeah, the single bundled PR was the right call here."

```markdown
---
name: bundled-prs-for-refactors
type: feedback
---
For tightly coupled refactors, prefer one bundled PR over many small ones.

**Why:** User confirmed this approach reduces churn. Splitting tightly 
coupled changes creates review overhead without improving clarity.

**How to apply:** When refactoring touches 3+ files that share a single 
logical change. Does NOT apply to independent feature additions.
```

### From Repeated Behavior

User: "I keep telling you — run the tests yourself, don't ask me to click buttons."

```markdown
---
name: autonomous-testing
type: feedback
---
Run, analyze, fix, repeat autonomously. Never ask the user to test manually 
when API/CLI access is available.

**Why:** User has limited patience for manual test cycles. 
Agent has full API access — no reason to involve the user.

**How to apply:** After any fix where automated verification is possible 
(API calls, CLI commands, test suites). Only ask the user when 
genuinely stuck or when human judgment is required.
```

## Storage

### Where to Store

Store feedback rules alongside your domain catalogs:

```
memory/
├── feedback/
│   ├── no-db-mocks-in-integration.md
│   ├── bundled-prs-for-refactors.md
│   └── autonomous-testing.md
├── catalogs/
│   ├── voice-pipeline.md
│   └── api-integration.md
└── patterns.md
```

### When to Review

- **Session start:** Load all feedback rules for the current project
- **Before suggesting an approach:** Check if any feedback rule applies
- **After user correction:** Create rule immediately (not "later")

## Quality Criteria

Good feedback rules have:
- **Specific scope** — "integration tests" not "all tests"
- **Clear why** — the reason, not just the rule
- **Edge case guidance** — enough context to judge when the rule applies and when it doesn't
- **Actionable check** — you can verify compliance, not just aspire to it

Bad feedback rules:
- "Be more careful" (not actionable)
- "Don't make mistakes" (not specific)
- "Follow best practices" (no why, no scope)
- Rules without `Why` (can't judge edge cases)

## The Compound Effect

Each feedback rule makes the agent slightly better at matching user expectations. Over 30+ rules, the agent's behavior shifts from "generic AI assistant" to "my AI assistant that knows how I work."

This is the mechanism that no current memory system implements well: not just storing facts, but actively shaping behavior through captured corrections and confirmations.
