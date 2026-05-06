"""DAP bridge — generates Debug Adapter Protocol commands from pattern strategies."""

import json
from pathlib import Path

from mcp.server import Server


def _extract_debugger_strategy(pattern_content: str) -> dict:
    lines = pattern_content.split("\n")
    in_strategy = False
    breakpoints = []
    watch_exprs = []
    isolation = ""
    expected = ""

    current_section = ""
    for line in lines:
        if "## Debugger Strategy" in line or "## debugger_strategy" in line.lower():
            in_strategy = True
            continue
        if in_strategy and line.startswith("## "):
            break
        if not in_strategy:
            continue

        if "**Breakpoints" in line or "**breakpoints" in line.lower():
            current_section = "breakpoints"
        elif "**Watch" in line or "**watch" in line.lower():
            current_section = "watch"
        elif "**Isolation" in line or "**isolation" in line.lower():
            current_section = "isolation"
        elif "**Expected" in line or "**expected" in line.lower():
            current_section = "expected"
        elif line.strip().startswith("- ") or line.strip().startswith("* "):
            item = line.strip().lstrip("-* ").strip()
            if current_section == "breakpoints":
                breakpoints.append(item)
            elif current_section == "watch":
                watch_exprs.append(item)
            elif current_section == "isolation":
                isolation += item + " "
            elif current_section == "expected":
                expected += item + " "

    return {
        "breakpoints": breakpoints,
        "watch_expressions": watch_exprs,
        "isolation_technique": isolation.strip(),
        "expected_evidence": expected.strip(),
    }


def _strategy_to_dap_commands(strategy: dict, file_path: str = "") -> list[dict]:
    commands = []

    for bp in strategy["breakpoints"]:
        cmd = {
            "command": "setBreakpoints",
            "arguments": {"source": {"path": file_path or "(from pattern)"}, "breakpoints": [{"line": 0}]},
            "note": bp,
        }
        commands.append(cmd)

    for expr in strategy["watch_expressions"]:
        commands.append({"command": "evaluate", "arguments": {"expression": expr, "context": "watch"}, "note": expr})

    return commands


def register(server: Server, repo_root: Path):
    patterns_dir = repo_root / "patterns"

    @server.tool()
    async def debug_dap_commands(pattern_id: str, file_path: str = "") -> str:
        """Generate DAP (Debug Adapter Protocol) commands from a pattern's debugger strategy.

        Returns JSON array of DAP-compatible commands with breakpoints and watch expressions
        derived from the matched pattern's strategy section.

        Args:
            pattern_id: Pattern ID (e.g., 'P02') to extract debugger strategy from
            file_path: Optional source file path for breakpoint targets
        """
        pattern_file = None
        normalized = pattern_id.upper()
        if not normalized.startswith("P"):
            normalized = f"P{normalized}"

        for f in patterns_dir.glob("*.md"):
            if f.name.upper().startswith(normalized.split("-")[0]) or normalized in f.name.upper():
                pattern_file = f
                break

        if not pattern_file:
            return json.dumps({"error": f"Pattern {pattern_id} not found"})

        content = pattern_file.read_text()
        strategy = _extract_debugger_strategy(content)

        if not strategy["breakpoints"] and not strategy["watch_expressions"]:
            return json.dumps({"error": f"No debugger strategy found in {pattern_id}", "raw_content": "Check pattern file for ## Debugger Strategy section"})

        commands = _strategy_to_dap_commands(strategy, file_path)

        result = {"pattern": pattern_id, "strategy": strategy, "dap_commands": commands}
        return json.dumps(result, indent=2)
