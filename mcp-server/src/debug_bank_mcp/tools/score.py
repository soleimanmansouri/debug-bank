"""debug_score — score a debugging trajectory against the 6-criterion rubric."""

from pathlib import Path

from mcp.server import Server

RUBRIC = {
    "pattern_check": {"max": 15, "desc": "Checked known patterns before investigating"},
    "reproduction": {"max": 15, "desc": "Reproduced the exact error with evidence"},
    "hypothesis_quality": {"max": 20, "desc": "Stated falsifiable hypotheses ranked by likelihood"},
    "isolation": {"max": 20, "desc": "Tested hypotheses systematically (binary search)"},
    "root_cause_depth": {"max": 15, "desc": "Found true root cause, not just symptom"},
    "fix_minimality": {"max": 15, "desc": "Minimal change addressing root cause only"},
}


def register(server: Server, repo_root: Path):
    @server.tool()
    async def debug_score(
        pattern_check: int = 0,
        reproduction: int = 0,
        hypothesis_quality: int = 0,
        isolation: int = 0,
        root_cause_depth: int = 0,
        fix_minimality: int = 0,
    ) -> str:
        """Score a debugging trajectory on the 6-criterion rubric (100 points total).

        Each criterion is scored 0 to its max. Returns total score and grade.

        Args:
            pattern_check: 0-15. Did the agent check known patterns first?
            reproduction: 0-15. Was the exact error reproduced with evidence?
            hypothesis_quality: 0-20. Were hypotheses falsifiable and ranked?
            isolation: 0-20. Were hypotheses tested systematically?
            root_cause_depth: 0-15. Was the true root cause found?
            fix_minimality: 0-15. Was the fix minimal and targeted?
        """
        scores = {
            "pattern_check": min(pattern_check, 15),
            "reproduction": min(reproduction, 15),
            "hypothesis_quality": min(hypothesis_quality, 20),
            "isolation": min(isolation, 20),
            "root_cause_depth": min(root_cause_depth, 15),
            "fix_minimality": min(fix_minimality, 15),
        }

        total = sum(scores.values())

        if total >= 90:
            grade = "A+"
        elif total >= 80:
            grade = "A"
        elif total >= 70:
            grade = "B"
        elif total >= 60:
            grade = "C"
        elif total >= 40:
            grade = "D"
        else:
            grade = "F"

        lines = [f"Total: {total}/100 ({grade})", ""]
        for key, val in scores.items():
            max_val = RUBRIC[key]["max"]
            desc = RUBRIC[key]["desc"]
            lines.append(f"  {key}: {val}/{max_val} — {desc}")

        return "\n".join(lines)
