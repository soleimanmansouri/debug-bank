"""debug_search — full-text search across all patterns."""

from pathlib import Path

from mcp.server import Server


def register(server: Server, repo_root: Path):
    patterns_dir = repo_root / "patterns"
    compositions_dir = repo_root / "compositions"

    @server.tool()
    async def debug_search(query: str, max_results: int = 5) -> str:
        """Search Debug Bank patterns by keyword. Returns matching excerpts.

        Args:
            query: Search term (e.g., 'cache invalidation', 'race condition', 'retry')
            max_results: Maximum number of results to return (default 5)
        """
        query_lower = query.lower()
        hits: list[tuple[str, str, int]] = []

        search_dirs = [patterns_dir, compositions_dir]
        for search_dir in search_dirs:
            if not search_dir.exists():
                continue
            for f in search_dir.glob("*.md"):
                content = f.read_text()
                content_lower = content.lower()
                count = content_lower.count(query_lower)
                if count > 0:
                    lines = content.split("\n")
                    title = next((l for l in lines if l.startswith("# ")), f.stem)
                    context_lines = [l.strip() for l in lines if query_lower in l.lower()][:3]
                    excerpt = "\n    ".join(context_lines)
                    hits.append((f.stem, f"{title}\n    {excerpt}", count))

        if not hits:
            return f"No results for '{query}'. Try broader terms or check pattern IDs directly."

        hits.sort(key=lambda x: -x[2])
        results = []
        for file_id, excerpt, count in hits[:max_results]:
            results.append(f"[{file_id}] ({count} hits)\n  {excerpt}")

        return "\n\n".join(results)
