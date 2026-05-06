"""debug_record — record a debugging trajectory to memory."""

import json
from datetime import datetime, timezone
from pathlib import Path

from mcp.server import Server

from ..memory.trajectory_store import TrajectoryStore


def register(server: Server, repo_root: Path):
    store = TrajectoryStore(repo_root / "memory" / "trajectories")

    @server.tool()
    async def debug_record(
        symptom: str,
        root_cause: str,
        fix: str,
        pattern_id: str = "",
        key_insight: str = "",
        files_changed: str = "",
    ) -> str:
        """Record a completed debugging trajectory for future pattern matching.

        Args:
            symptom: What the user/system saw (the bug report)
            root_cause: The actual technical root cause identified
            fix: What was changed (file:line description)
            pattern_id: Matched pattern ID if any (e.g., 'P02')
            key_insight: Generalizable lesson from this fix
            files_changed: Comma-separated list of files modified
        """
        trajectory = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "symptom": symptom,
            "root_cause": root_cause,
            "fix": fix,
            "pattern_id": pattern_id or "novel",
            "key_insight": key_insight,
            "files_changed": [f.strip() for f in files_changed.split(",") if f.strip()],
        }

        entry_id = store.save(trajectory)
        return f"Trajectory recorded: {entry_id}\nPattern: {trajectory['pattern_id']}\nInsight: {key_insight or '(none)'}"
