"""debug_pattern — retrieve full pattern content by ID."""

from pathlib import Path
from typing import Optional

from mcp.server import Server


def _find_pattern_file(patterns_dir: Path, pattern_id: str) -> Optional[Path]:
    normalized = pattern_id.upper().replace("P", "P0") if len(pattern_id) == 2 else pattern_id.upper()
    if not normalized.startswith("P"):
        normalized = f"P{normalized}"

    for f in patterns_dir.glob("*.md"):
        if f.name.upper().startswith(normalized.split("-")[0]) or normalized in f.name.upper():
            return f

    for f in patterns_dir.glob("*.md"):
        if pattern_id.lower() in f.name.lower():
            return f

    return None


def register(server: Server, repo_root: Path):
    patterns_dir = repo_root / "patterns"

    @server.tool()
    async def debug_pattern(pattern_id: str, section: str = "") -> str:
        """Retrieve a Debug Bank pattern by ID (e.g., 'P02', 'P08').

        Args:
            pattern_id: Pattern identifier like P01, P02, ..., P22
            section: Optional section to extract (e.g., 'debugger_strategy', 'checklist', 'fix')
        """
        path = _find_pattern_file(patterns_dir, pattern_id)
        if not path:
            available = sorted(f.stem for f in patterns_dir.glob("P*.md"))
            return f"Pattern {pattern_id} not found. Available: {', '.join(available)}"

        content = path.read_text()

        if section:
            section_lower = section.lower().replace("_", " ")
            lines = content.split("\n")
            capture = False
            result = []
            for line in lines:
                if line.startswith("##") and section_lower in line.lower():
                    capture = True
                    result.append(line)
                elif capture and line.startswith("##"):
                    break
                elif capture:
                    result.append(line)
            if result:
                return "\n".join(result)
            return f"Section '{section}' not found in {pattern_id}. Full pattern returned.\n\n{content}"

        return content
