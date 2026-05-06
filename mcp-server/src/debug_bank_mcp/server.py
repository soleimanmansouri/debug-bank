"""Debug Bank MCP Server — exposes patterns, classifier, and trajectory memory."""

import asyncio
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server

from .tools.classify import register as register_classify
from .tools.pattern import register as register_pattern
from .tools.search import register as register_search
from .tools.record import register as register_record
from .tools.score import register as register_score
from .bridge.dap_bridge import register as register_dap

REPO_ROOT = Path(__file__).resolve().parents[4]

server = Server("debug-bank")


def _register_all():
    register_classify(server, REPO_ROOT)
    register_pattern(server, REPO_ROOT)
    register_search(server, REPO_ROOT)
    register_record(server, REPO_ROOT)
    register_score(server, REPO_ROOT)
    register_dap(server, REPO_ROOT)


async def _run():
    _register_all()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main():
    asyncio.run(_run())


if __name__ == "__main__":
    main()
