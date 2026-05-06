# Debug-Bench

**The first benchmark that scores debugging quality, not just pass/fail.**

Most benchmarks ask: "did you fix it?" Debug-Bench asks: "how well did you debug it?" A correct fix reached through principled investigation scores higher than the same fix reached by guessing.

Debug-Bench turns Debug Bank's scenario library into runnable Docker environments with pre-injected bugs, observable symptoms, and a trajectory scorer that rewards structured investigation.

## How It Works

1. **Start a scenario** — Docker spins up the multi-service environment with the bug pre-injected
2. **Investigate** — the agent interacts with running services, reads logs, traces requests
3. **Record a trajectory** — structured JSON documenting each investigation step
4. **Score** — `score.py` evaluates the trajectory against the rubric

## Scenarios

| ID | Name | Patterns | Services | Difficulty |
|----|------|----------|----------|------------|
| S01 | Stale Cache Race | P02, P08 | Node.js gateway, Python order service, Go cache invalidator, Redis, Postgres, RabbitMQ | L4 |
| S02 | Retry Storm Amplification | P06, P03 | Python API server, Python downstream service | L4 |
| S03 | Silent Schema Drift | P07, P02, P13 | Python service-a (schema owner), Python service-b (dispatcher), Redis, Postgres | L3 |

## Quick Start

### Prerequisites
- Docker + Docker Compose v2
- Python 3.10+ with PyYAML (`pip install pyyaml`)

### Run a scenario

```bash
# Start the environment
./run-bench.sh S01

# The runner prints the symptom description and service URLs.
# Investigate the running system, then record your findings.

# Tear down when done
./run-bench.sh S01 --down
```

### Score a trajectory

```bash
python scoring/score.py --trajectory my-trajectory.json --scenario S01
```

Or pipe JSON output:

```bash
python scoring/score.py --trajectory my-trajectory.json --scenario S01 --json
```

## Trajectory Format

An agent (or human) produces a `trajectory.json` documenting the investigation:

```json
{
  "scenario": "S01",
  "agent": "my-agent-v1",
  "steps": [
    {
      "step": 1,
      "action": "pattern_check",
      "content": "Symptom: intermittent stale data after writes. Checking P02 (multiple writers) and P08 (config chain gap). Both match."
    },
    {
      "step": 2,
      "action": "reproduce",
      "content": "Updated price for P001, sent 50 concurrent GET requests. 8 returned old price."
    },
    {
      "step": 3,
      "action": "hypothesize",
      "content": "H1: read-through cache re-fills stale data after invalidation. H2: event bus delay. H3: replica lag alone."
    },
    {
      "step": 4,
      "action": "isolate",
      "content": "Added Redis MONITOR. Saw DEL price:P001 at T+80ms, then SET price:P001 (old value) at T+155ms. SET is from read-through fill."
    },
    {
      "step": 5,
      "action": "diagnose",
      "content": "Order Service returns stale price from replica during lag window. API Gateway read-through writes this stale value AFTER the invalidator deleted the key."
    },
    {
      "step": 6,
      "action": "fix",
      "content": "Added version stamp to Order Service response. Read-through fill now does a conditional write: only SET if version >= cached version."
    }
  ],
  "root_cause": "Read-through cache re-fills stale data from replica after invalidation",
  "fix": "Conditional write with version stamp — only update cache if returned version is newer",
  "trajectory_record": {
    "symptom": "15% of requests see old price for 30-90s after price update",
    "root_cause": "Read-through fill overwrites post-invalidation slot with stale replica data",
    "fix": "Version stamp conditional write in API Gateway read-through path",
    "key_insight": "Read-through cache is a second writer — P02 applies whenever there is also an invalidator"
  }
}
```

## Scoring Rubric

| Criterion | Points | What Gets Credit |
|-----------|--------|-----------------|
| Checked patterns before investigating | 20 | Named a pattern or ran pattern check in first 3 steps |
| Found root cause (not symptom) | 20 | Root cause matches solution.yml (50%+ keyword overlap) |
| Minimal steps to diagnosis | 15 | Steps taken <= expected_steps from scoring.yml |
| Avoided red herrings | 15 | Did not spend 2+ steps on any listed red herring |
| Fix addresses root cause | 15 | Fix contains a keyword from solution.yml:fix_keywords |
| Recorded trajectory | 15 | Trajectory record has symptom, root cause, fix, key insight |
| **Total** | **100** | |

Grades: A+ (90-100), A (80-89), B (70-79), C (60-69), D (50-59), F (<50)

Full rubric: [scoring/rubric.md](scoring/rubric.md)

## Adding a New Scenario

1. Create `challenges/SXX-scenario-name/`
2. Add `docker-compose.yml` with services implementing the bug
3. Add `scoring.yml` — scenario metadata, expected_steps, red_herrings, fix_keywords
4. Add `solution.yml` — root cause description and fix approach
5. Add `services/*/` — minimal service implementations (50-100 lines each)
6. Update this README with the new scenario row

See [scoring/rubric.md](scoring/rubric.md) for guidance on setting expected_steps and choosing red herrings.

## Design Principles

- **Minimal services** — each service is 50-100 lines, just enough to demonstrate the bug
- **Observable symptoms** — every scenario has a measurable observable symptom (% stale reads, amplification ratio, silent feature failure)
- **Falsifiable red herrings** — each red herring has a specific test that disproves it
- **Score stability** — scoring is keyword-based and reproducible, not subjective
