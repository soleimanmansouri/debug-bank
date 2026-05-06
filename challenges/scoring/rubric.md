# Debug-Bench Universal Scoring Rubric

Debug-Bench scores debugging **quality**, not just pass/fail. A correct fix reached by brute force scores lower than a correct fix reached by principled investigation.

## Scoring Criteria

| # | Criterion | Points | What Gets Credit |
|---|-----------|--------|-----------------|
| 1 | Checked patterns before investigating | 20 | Agent output explicitly mentions a pattern check, names a pattern (P01–P16), or references the pattern classifier before forming hypotheses |
| 2 | Found root cause (not symptom) | 20 | Agent identifies the actual root cause from `solution.yml` — not a red herring, not a downstream symptom |
| 3 | Minimal steps to diagnosis | 15 | Total investigation steps <= `expected_steps` from `scoring.yml`. Partial credit: within 2x expected |
| 4 | Avoided red herrings | 15 | Agent did NOT spend more than one step pursuing any item listed in `scoring.yml:red_herrings`. Spending 2+ steps on a red herring = 0 points for this criterion |
| 5 | Fix addresses root cause | 15 | Fix contains at least one keyword from `solution.yml:fix_keywords`, OR is equivalent to the described fix |
| 6 | Recorded trajectory | 15 | Agent produced a trajectory record with at minimum: symptom, root cause, fix, key insight |

**Total: 100 points**

## Grade Scale

| Score | Grade | Meaning |
|-------|-------|---------|
| 90–100 | A+ | Textbook trajectory — patterns first, minimal steps, clean fix |
| 80–89 | A | Strong — correct diagnosis, minor inefficiency |
| 70–79 | B | Correct fix but took extra steps or skipped pattern check |
| 60–69 | C | Found fix but pursued red herrings or missed root cause framing |
| 50–59 | D | Stumbled to the fix without structured investigation |
| 0–49 | F | Wrong fix, or correct fix with no traceable reasoning |

## How Scores Are Computed

Scoring is done by `score.py`. It reads a trajectory JSON file and the per-scenario `scoring.yml`.

### Trajectory JSON format

The agent (or harness) produces a `trajectory.json` file documenting the investigation:

```json
{
  "scenario": "S01",
  "agent": "gpt-4o",
  "steps": [
    {
      "step": 1,
      "action": "pattern_check",
      "content": "Checking P02 (Multiple Writers) and P08 (Config Chain Gap) — both match intermittent stale data after writes."
    },
    {
      "step": 2,
      "action": "reproduce",
      "content": "Ran 100 concurrent requests after price update. 14 returned old price."
    }
  ],
  "root_cause": "Read-through cache re-fills stale data from replica after invalidation",
  "fix": "Added version stamp to cache entries, conditional write only if version >= cached version",
  "trajectory_record": {
    "symptom": "15% of requests see old price for 30-90s after update",
    "root_cause": "Read-through cache re-fills from replica after invalidation",
    "fix": "Conditional cache write with version stamp (app.js:47)",
    "key_insight": "Read-through cache is a second writer — P02 applies"
  }
}
```

### Criterion evaluation

**Criterion 1 (Pattern Check):** Looks for `"action": "pattern_check"` in steps, OR keywords `"P0"`, `"pattern"`, `"P1"`, `"P2"` in the first 3 steps' content.

**Criterion 2 (Root Cause):** Compares `trajectory.root_cause` against `solution.yml:root_cause` using keyword overlap (>=50% of root cause keywords must match).

**Criterion 3 (Minimal Steps):** `len(trajectory.steps) <= scoring.yml:expected_steps` → full credit. Within `2 * expected_steps` → 8 points. Over → 0.

**Criterion 4 (Red Herrings):** For each item in `scoring.yml:red_herrings`, count steps where content mentions that red herring. If any red herring appears in 2+ steps → criterion score = 0.

**Criterion 5 (Fix Keywords):** Checks `trajectory.fix` for any keyword in `solution.yml:fix_keywords`. Case-insensitive.

**Criterion 6 (Trajectory Record):** Checks that `trajectory.trajectory_record` contains non-empty `symptom`, `root_cause`, `fix`, and `key_insight` fields.

## Adding New Scenarios

When adding a scenario to Debug-Bench:

1. Set `expected_steps` by running through the scenario yourself and counting investigation steps.
2. List red herrings explicitly — these must be testable (the scenario architecture must make them look plausible).
3. List `fix_keywords` that are unambiguous indicators of the correct fix approach.
4. Write a `solution.yml` that a scorer can validate against without subjective judgment.
