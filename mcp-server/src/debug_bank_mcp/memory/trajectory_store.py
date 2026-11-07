"""Trajectory store — persists debugging trajectories as JSON files."""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


class TrajectoryStore:
    def __init__(self, store_dir: Path):
        self.store_dir = store_dir
        self.store_dir.mkdir(parents=True, exist_ok=True)

    def save(self, trajectory: dict) -> str:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        pattern = trajectory.get("pattern_id", "novel")
        # Random suffix: ids were second-resolution, so two records in the same
        # second overwrote each other. "x" mode refuses to overwrite regardless.
        entry_id = f"{ts}-{pattern}-{uuid.uuid4().hex[:8]}"
        path = self.store_dir / f"{entry_id}.json"
        with path.open("x") as fh:
            fh.write(json.dumps(trajectory, indent=2))
        return entry_id

    def search(self, query: str, limit: int = 10) -> list[dict]:
        query_lower = query.lower()
        results = []
        if not self.store_dir.exists():
            return results

        for f in sorted(self.store_dir.glob("*.json"), reverse=True):
            try:
                data = json.loads(f.read_text())
                searchable = json.dumps(data).lower()
                if query_lower in searchable:
                    data["_id"] = f.stem
                    results.append(data)
                    if len(results) >= limit:
                        break
            except (json.JSONDecodeError, OSError):
                continue
        return results

    def list_recent(self, limit: int = 20) -> list[dict]:
        results = []
        if not self.store_dir.exists():
            return results

        for f in sorted(self.store_dir.glob("*.json"), reverse=True)[:limit]:
            try:
                data = json.loads(f.read_text())
                data["_id"] = f.stem
                results.append(data)
            except (json.JSONDecodeError, OSError):
                continue
        return results
