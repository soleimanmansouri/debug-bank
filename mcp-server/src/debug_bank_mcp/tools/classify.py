"""debug_classify — map symptom description to ranked pattern matches."""

import re
from pathlib import Path

from mcp.server import Server

KEYWORD_INDEX: list[tuple[str, str, list[str]]] = [
    ("duplicate output, sent twice, N copies, message multiplied", "P03", ["P01", "P20"]),
    ("duplicate output exactly twice, response spoken twice, double output", "P01", ["P03"]),
    ("stale data, old value, cached but wrong, outdated response", "P07", ["P08", "P02"]),
    ("works here breaks there, context-dependent, env-specific", "P05", ["P10", "P21"]),
    ("config change no effect, setting ignored, reload has no impact", "P07", ["P08", "P10"]),
    ("after dependency update, after upgrade, after version bump", "P06", ["P01"]),
    ("wrong department, wrong number, wrong fallback, routes incorrectly", "P08", ["P07", "P10"]),
    ("overwrites, last writer wins, data loss, field reset", "P02", ["P09"]),
    ("error code treated as data, false success, HTTP 4xx as value", "P13", ["P08"]),
    ("literal template text, $credentials shown, raw variable in output", "P11", ["P14"]),
    ("XML corrupted, YAML mangled, body altered, payload damaged", "P12", []),
    ("expression not evaluated, literal {{ in output, template as string", "P14", ["P11"]),
    ("multi-output node rejects valid format, branch routing fails", "P15", []),
    ("binary data is string or URL instead of bytes, file attachment broken", "P16", []),
    ("LLM repeats example text verbatim, copies few-shot sample", "P04", ["P17"]),
    ("model speaks history aloud, agent reads context as dialogue", "P17", ["P04"]),
    ("farewell loop, repeating goodbye, goodbye fires multiple times", "P18", ["P19"]),
    ("prompt fix doesn't work after 2 tries, instruction ignored", "P19", ["P17", "P18"]),
    ("filler blocks transfer, queue saturated, audio pile-up before handoff", "P20", ["P02", "P03"]),
    ("works for handler A breaks handler B, untested code path", "P21", ["P05", "P20"]),
    ("same bug fixed 3+ times still broken, patch regression, fix undone", "P22", ["P18", "P19"]),
    ("wrapper inherits wrong default, subclass wrong base value", "P01", ["P06"]),
    ("free-text written as structured field, narrative in typed column", "P09", ["P02"]),
    ("provider mismatch, wrong voice ID, wrong model ID, wrong API target", "P10", ["P07", "P08"]),
]

COMPOUND_INDEX: list[tuple[str, list[str], str]] = [
    ("intermittent wrong price, race on concurrent writes", ["P02", "P08"], "C01"),
    ("retry storm, traffic amplification after upgrade", ["P06", "P03"], "C02"),
    ("no errors but wrong results, 100% success rate with bad data", ["P13", "P07"], "C03"),
]


def _score_match(symptom: str, keywords: str) -> int:
    tokens = [k.strip().lower() for k in keywords.split(",")]
    symptom_lower = symptom.lower()
    return sum(1 for t in tokens if t in symptom_lower)


def classify(symptom: str) -> dict:
    scores: dict[str, float] = {}

    for keywords, primary, secondaries in KEYWORD_INDEX:
        score = _score_match(symptom, keywords)
        if score > 0:
            scores[primary] = scores.get(primary, 0) + score * 2
            for s in secondaries:
                scores[s] = scores.get(s, 0) + score

    for keywords, patterns, composition in COMPOUND_INDEX:
        score = _score_match(symptom, keywords)
        if score > 0:
            scores[composition] = scores.get(composition, 0) + score * 3

    if not scores:
        return {"matches": [], "confidence": "none", "recommendation": "Use auto-instrumentation fallback"}

    ranked = sorted(scores.items(), key=lambda x: -x[1])
    top_score = ranked[0][1]

    confidence = "high" if top_score >= 4 else "medium" if top_score >= 2 else "low"

    matches = [{"pattern": p, "score": s, "rank": i + 1} for i, (p, s) in enumerate(ranked[:5])]

    return {"matches": matches, "confidence": confidence, "recommendation": f"Start with {ranked[0][0]} checklist"}


def register(server: Server, repo_root: Path):
    @server.tool()
    async def debug_classify(symptom: str) -> str:
        """Classify a bug symptom into ranked Debug Bank pattern matches.

        Args:
            symptom: Natural language description of the bug symptom
        """
        result = classify(symptom)
        lines = [f"Confidence: {result['confidence']}", f"Recommendation: {result['recommendation']}", ""]
        for m in result.get("matches", []):
            lines.append(f"  #{m['rank']} {m['pattern']} (score: {m['score']})")
        return "\n".join(lines)
