"""Debug Bank MCP Server — exposes patterns, classifier, and trajectory memory."""

from pathlib import Path

# The tool modules register with @server.tool(), which is FastMCP's API;
# the low-level mcp.server.Server has no .tool() and crashed on startup.
from mcp.server.fastmcp import FastMCP

from .tools.classify import register as register_classify
from .tools.pattern import register as register_pattern
from .tools.search import register as register_search
from .tools.record import register as register_record
from .tools.score import register as register_score
from .bridge.dap_bridge import register as register_dap

REPO_ROOT = Path(__file__).resolve().parents[3]  # src/debug_bank_mcp/server.py -> debug-bank/

server = FastMCP("debug-bank")


def _register_all():
    register_classify(server, REPO_ROOT)
    register_pattern(server, REPO_ROOT)
    register_search(server, REPO_ROOT)
    register_record(server, REPO_ROOT)
    register_score(server, REPO_ROOT)
    register_dap(server, REPO_ROOT)


def main():
    _register_all()
    server.run()  # stdio


if __name__ == "__main__":
    main()
