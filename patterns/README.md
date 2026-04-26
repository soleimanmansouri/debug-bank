# Pattern Bank

## What Are Patterns?

Patterns are generalized root cause types extracted from real debugging sessions. Each pattern describes a CLASS of bug — not a specific instance — with diagnostic questions that help identify it in 30 seconds.

## How to Use

### During Debugging (Step 1 of the Protocol)

1. Read the symptom description
2. Scan the pattern table below
3. If one matches, read the full pattern file
4. Verify the known fix applies to your specific case
5. If no match, proceed to Step 2 (Reproduce)

### Pattern Quick Reference

| ID | Pattern | Quick Check |
|----|---------|-------------|
| P01 | Wrapper/Decorator Default Mismatch | Audit ALL parent class defaults when wrapping |
| P02 | Multiple Write Sources → Corruption | Grep for ALL writes to the same target |
| P03 | Observer/Hook Multiplier | Deduplicate by event/frame ID |
| P04 | LLM Copies Example Text as Behavior | No action-like text in prompts |
| P05 | Context-Dependent Flag Duality | Check if any context needs the opposite value |
| P06 | Dependency Resolution Cascade | Check lock file after adding any dependency |
| P07 | Stale/Dead Config | Trace where runtime actually reads from |
| P08 | Config Resolution Chain Gap | Trace the full fallback chain |
| P09 | Auto-Apply Pipeline Writing Feedback as Data | Validate payload matches target field |
| P10 | Contradictory Multi-Source Config | Validate ALL sibling fields match provider |
| P11 | Credential Expression Scope Limitation | Test credential expressions with echo/log |
| P12 | Expression Engine Corrupts Non-JSON Bodies | Use JSON-based APIs in workflow engines |
| P13 | Parse Code Matches Errors as Success | Check error indicators BEFORE extracting data |
| P14 | Expression Evaluation Requires Prefix | Add prefix if template renders as literal text |
| P15 | Multi-Output Node Rejects Valid Returns | Use parallel single-output nodes instead |
| P16 | Binary Data Is Reference-Based | Use helper methods to read actual data |
| P17 | Model Speaks Everything in Context | Keep speakable text out of conversation history |
| P18 | Model Loops Without Stop Signal | Set precise timeouts, add idempotency guards |
| P19 | Prompt Engineering Has Hard Limits | Switch to code-level after 2 failed prompt fixes |

## Pattern Categories

- **Code Structure** (P01, P03, P05): Bugs from how code is organized
- **Data Integrity** (P02, P09): Bugs from competing data writers
- **Configuration** (P07, P08, P10): Bugs from multi-source config
- **Dependencies** (P06): Bugs from package management
- **Platform Quirks** (P11-P16): Bugs from platform-specific behavior
- **LLM/AI** (P04, P17-P19): Bugs specific to AI/LLM systems

## Adding New Patterns

When 3+ bugs in your domain catalogs share a root cause type not covered by existing patterns:

1. Copy `TEMPLATE.md`
2. Assign the next P-number (P20, P21, etc.)
3. Fill in all sections
4. Add to the quick reference table above
5. Submit a PR with a real-world example

### Quality Bar

A good pattern is:
- **Generalizable** — applies across projects, not just one codebase
- **Diagnosable in 30 seconds** — the check list produces a yes/no answer quickly
- **Falsifiable** — you can verify whether the pattern matches or doesn't
- **Actionable** — the fix section tells you exactly what to change

A bad pattern is:
- Too specific ("React useState doesn't update immediately") — that's a known behavior, not a pattern
- Too vague ("Code doesn't work as expected") — every bug matches this
- Not falsifiable ("Something is wrong with the config") — can't verify in 30 seconds
