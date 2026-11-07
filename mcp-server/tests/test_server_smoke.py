"""Smoke test: the server starts, exposes its six tools, and finds the pattern bank.

Both checks failed before (wrong repo root, low-level Server without .tool()),
so this guards exactly what users hit first. Run: python -m unittest discover tests
"""
import asyncio
import unittest

from debug_bank_mcp import server as srv


class ServerSmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        srv._register_all()

    def test_repo_root_has_patterns(self):
        self.assertTrue((srv.REPO_ROOT / "patterns").is_dir(), srv.REPO_ROOT)

    def test_six_tools_registered(self):
        names = {t.name for t in asyncio.run(srv.server.list_tools())}
        self.assertEqual(names, {"debug_classify", "debug_pattern", "debug_search",
                                 "debug_record", "debug_score", "debug_dap_commands"})

    def test_pattern_lookup_returns_content(self):
        result = asyncio.run(srv.server.call_tool("debug_pattern", {"pattern_id": "P26"}))
        content = result[0] if isinstance(result, tuple) else result
        self.assertIn("P26", "".join(getattr(c, "text", "") for c in content))


if __name__ == "__main__":
    unittest.main()
