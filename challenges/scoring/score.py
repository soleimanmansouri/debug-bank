#!/usr/bin/env python3
"""
Debug-Bench Trajectory Scorer

Reads a trajectory JSON file and a scenario scoring.yml, outputs a score.

Usage:
    python scoring/score.py --trajectory trajectory.json --scenario S01
    python scoring/score.py --trajectory trajectory.json --scoring challenges/S01-stale-cache-race/scoring.yml
"""

import argparse
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Error: PyYAML required. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


SCENARIO_DIRS = {
    "S01": "S01-stale-cache-race",
    "S02": "S02-retry-storm",
    "S03": "S03-silent-schema-drift",
}

GRADE_SCALE = [
    (90, "A+"),
    (80, "A"),
    (70, "B"),
    (60, "C"),
    (50, "D"),
    (0,  "F"),
]


def grade(score: int) -> str:
    for threshold, letter in GRADE_SCALE:
        if score >= threshold:
            return letter
    return "F"


def score_pattern_check(steps: list) -> tuple[int, str]:
    """Criterion 1: checked patterns before investigating (20 pts)."""
    pattern_keywords = ["p0", "p1", "p2", "pattern", "pattern check", "classifier"]
    # Check first 3 steps for pattern check action or keywords
    for step in steps[:3]:
        action = step.get("action", "").lower()
        content = step.get("content", "").lower()
        if action == "pattern_check":
            return 20, "Explicit pattern_check action found in first 3 steps"
        if any(kw in content for kw in pattern_keywords):
            return 20, f"Pattern reference found in step {step.get('step', '?')}"
    # Also check if any step has action=pattern_check
    for step in steps:
        if step.get("action", "").lower() == "pattern_check":
            return 10, "Pattern check found but not in first 3 steps (partial credit)"
    return 0, "No pattern check found"


def score_root_cause(trajectory_root_cause: str, solution_root_cause: str) -> tuple[int, str]:
    """Criterion 2: found root cause not symptom (20 pts)."""
    if not trajectory_root_cause or not solution_root_cause:
        return 0, "Missing root_cause field"

    # Tokenize and check keyword overlap
    traj_words = set(trajectory_root_cause.lower().split())
    sol_words = set(solution_root_cause.lower().split())
    # Remove common stop words
    stop_words = {"the", "a", "an", "is", "in", "on", "at", "to", "of", "and", "or", "with",
                  "from", "after", "before", "by", "for", "not", "that", "this", "it"}
    sol_keywords = sol_words - stop_words
    if not sol_keywords:
        return 0, "Solution root cause has no meaningful keywords"

    overlap = traj_words & sol_keywords
    ratio = len(overlap) / len(sol_keywords)

    if ratio >= 0.5:
        return 20, f"Root cause match: {ratio:.0%} keyword overlap ({', '.join(sorted(overlap)[:5])})"
    elif ratio >= 0.3:
        return 10, f"Partial root cause match: {ratio:.0%} keyword overlap"
    else:
        return 0, f"Root cause mismatch: only {ratio:.0%} keyword overlap"


def score_minimal_steps(steps: list, expected_steps: int) -> tuple[int, str]:
    """Criterion 3: minimal steps to diagnosis (15 pts)."""
    actual = len(steps)
    if actual <= expected_steps:
        return 15, f"Steps taken ({actual}) <= expected ({expected_steps})"
    elif actual <= expected_steps * 2:
        return 8, f"Steps taken ({actual}) within 2x expected ({expected_steps})"
    else:
        return 0, f"Steps taken ({actual}) exceeds 2x expected ({expected_steps})"


def score_red_herrings(steps: list, red_herrings: list) -> tuple[int, str]:
    """Criterion 4: avoided red herrings (15 pts).

    A red herring is only penalised when the agent actively PURSUES it —
    i.e. spends investigative steps on it. Listing something as a wrong
    hypothesis (action=hypothesize) or explicitly falsifying it in one
    step does NOT count as pursuing it.
    """
    if not red_herrings:
        return 15, "No red herrings defined for this scenario"

    # Actions that indicate active pursuit rather than enumeration/dismissal
    PURSUIT_ACTIONS = {"isolate", "reproduce", "investigate", "check", "debug", "test"}

    violations = []
    for herring in red_herrings:
        herring_lower = herring.lower()
        # Use first few distinctive words as signal
        herring_words = [w for w in herring_lower.split() if len(w) > 4][:4]
        # For a single-word herring, require an exact phrase match instead
        use_phrase = len(herring_words) <= 1
        pursuit_count = 0
        for step in steps:
            content = step.get("content", "").lower()
            action = step.get("action", "").lower()
            # Match: require at least 2 distinctive words to co-occur in the
            # same step, OR exact phrase match for short herrings.
            if use_phrase:
                matched = herring_lower in content
            else:
                matched = sum(1 for w in herring_words if w in content) >= 2

            if matched:
                # Only count as pursuit if the step action is investigative
                # and not just a hypothesis enumeration or explicit dismissal
                if action in PURSUIT_ACTIONS or (
                    action not in {"hypothesize", "pattern_check"} and
                    "wrong" not in content and
                    "not the" not in content and
                    "ruled out" not in content and
                    "falsif" not in content
                ):
                    pursuit_count += 1
        if pursuit_count >= 2:
            violations.append(f'"{herring}" (pursued in {pursuit_count} steps)')

    if violations:
        return 0, f"Pursued red herrings: {'; '.join(violations)}"
    return 15, "No red herrings pursued"


def score_fix_keywords(fix: str, fix_keywords: list) -> tuple[int, str]:
    """Criterion 5: fix addresses root cause (15 pts)."""
    if not fix:
        return 0, "No fix field in trajectory"
    fix_lower = fix.lower()
    matched = [kw for kw in fix_keywords if kw.lower() in fix_lower]
    if matched:
        return 15, f"Fix keyword match: {matched}"
    return 0, f"No fix keywords found. Expected one of: {fix_keywords}"


def score_trajectory_record(record: dict) -> tuple[int, str]:
    """Criterion 6: recorded trajectory (15 pts)."""
    if not record:
        return 0, "No trajectory_record field"
    required = ["symptom", "root_cause", "fix", "key_insight"]
    missing = [f for f in required if not record.get(f)]
    if not missing:
        return 15, "Complete trajectory record with all required fields"
    elif len(missing) <= 2:
        return 8, f"Partial trajectory record — missing: {missing}"
    return 0, f"Incomplete trajectory record — missing: {missing}"


def score_trajectory(trajectory: dict, scoring: dict) -> dict:
    steps = trajectory.get("steps", [])
    solution_root_cause = scoring.get("root_cause", "")
    expected_steps = scoring.get("expected_steps", 10)
    red_herrings = scoring.get("red_herrings", [])
    fix_keywords = scoring.get("fix_keywords", [])

    c1_pts, c1_note = score_pattern_check(steps)
    c2_pts, c2_note = score_root_cause(trajectory.get("root_cause", ""), solution_root_cause)
    c3_pts, c3_note = score_minimal_steps(steps, expected_steps)
    c4_pts, c4_note = score_red_herrings(steps, red_herrings)
    c5_pts, c5_note = score_fix_keywords(trajectory.get("fix", ""), fix_keywords)
    c6_pts, c6_note = score_trajectory_record(trajectory.get("trajectory_record", {}))

    total = c1_pts + c2_pts + c3_pts + c4_pts + c5_pts + c6_pts

    return {
        "score": total,
        "grade": grade(total),
        "scenario": scoring.get("scenario", trajectory.get("scenario", "?")),
        "agent": trajectory.get("agent", "unknown"),
        "details": {
            "pattern_check":       {"points": c1_pts, "max": 20, "note": c1_note},
            "root_cause":          {"points": c2_pts, "max": 20, "note": c2_note},
            "minimal_steps":       {"points": c3_pts, "max": 15, "note": c3_note},
            "avoided_red_herrings":{"points": c4_pts, "max": 15, "note": c4_note},
            "fix_quality":         {"points": c5_pts, "max": 15, "note": c5_note},
            "trajectory_recorded": {"points": c6_pts, "max": 15, "note": c6_note},
        }
    }


def find_scoring_yml(scenario_id: str, base_dir: Path) -> Path:
    dir_name = SCENARIO_DIRS.get(scenario_id.upper())
    if not dir_name:
        raise FileNotFoundError(f"Unknown scenario: {scenario_id}. Known: {list(SCENARIO_DIRS)}")
    path = base_dir / dir_name / "scoring.yml"
    if not path.exists():
        raise FileNotFoundError(f"scoring.yml not found at {path}")
    return path


def main():
    parser = argparse.ArgumentParser(
        description="Score a Debug-Bench trajectory against a scenario rubric."
    )
    parser.add_argument("--trajectory", required=True, help="Path to trajectory JSON file")
    parser.add_argument("--scenario", help="Scenario ID (e.g. S01). Used to find scoring.yml automatically.")
    parser.add_argument("--scoring", help="Explicit path to scoring.yml (overrides --scenario lookup)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON (default: human-readable)")
    args = parser.parse_args()

    # Load trajectory
    traj_path = Path(args.trajectory)
    if not traj_path.exists():
        print(f"Error: trajectory file not found: {traj_path}", file=sys.stderr)
        sys.exit(1)
    with open(traj_path) as f:
        trajectory = json.load(f)

    # Locate scoring.yml
    if args.scoring:
        scoring_path = Path(args.scoring)
    elif args.scenario:
        # Resolve relative to this script's parent (challenges/)
        base = Path(__file__).parent.parent
        scoring_path = find_scoring_yml(args.scenario, base)
    else:
        # Try reading scenario from trajectory file
        scenario_id = trajectory.get("scenario")
        if not scenario_id:
            print("Error: provide --scenario or --scoring, or include 'scenario' in trajectory JSON.", file=sys.stderr)
            sys.exit(1)
        base = Path(__file__).parent.parent
        scoring_path = find_scoring_yml(scenario_id, base)

    if not scoring_path.exists():
        print(f"Error: scoring.yml not found: {scoring_path}", file=sys.stderr)
        sys.exit(1)

    with open(scoring_path) as f:
        scoring = yaml.safe_load(f)

    result = score_trajectory(trajectory, scoring)

    if args.json:
        print(json.dumps(result, indent=2))
        return

    # Human-readable output
    print(f"\nDebug-Bench Score Report")
    print(f"{'='*40}")
    print(f"Scenario : {result['scenario']}")
    print(f"Agent    : {result['agent']}")
    print(f"Score    : {result['score']}/100  ({result['grade']})")
    print(f"{'='*40}")
    details = result["details"]
    rows = [
        ("Pattern check",        details["pattern_check"]),
        ("Root cause",           details["root_cause"]),
        ("Minimal steps",        details["minimal_steps"]),
        ("Avoided red herrings", details["avoided_red_herrings"]),
        ("Fix quality",          details["fix_quality"]),
        ("Trajectory recorded",  details["trajectory_recorded"]),
    ]
    for name, d in rows:
        bar = "#" * d["points"] + "." * (d["max"] - d["points"])
        print(f"  {name:<22} {d['points']:>2}/{d['max']}  [{bar}]")
        print(f"    {d['note']}")
    print()


if __name__ == "__main__":
    main()
