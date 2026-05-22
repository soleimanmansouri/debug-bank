# Debug Bank MCP Server

MCP server that exposes Debug Bank's 24 patterns, symptom classifier, trajectory memory, and DAP bridge as tools any MCP-compatible client can call.

## Installation

```bash
cd mcp-server
pip install -e .
```

With DAP support (for debugpy integration):
```bash
pip install -e ".[dap]"
```

## Usage

### Claude Code

Add to your MCP settings (`~/.claude/mcp_servers.json`):

```json
{
  "debug-bank": {
    "command": "debug-bank-mcp",
    "args": []
  }
}
```

### Any MCP client

```bash
debug-bank-mcp
```

The server communicates over stdio using the MCP protocol.

## Tools

| Tool | Description |
|------|-------------|
| `debug_classify` | Map a symptom description to ranked pattern matches with confidence |
| `debug_pattern` | Retrieve full pattern content by ID (P01-P24), optionally a specific section |
| `debug_search` | Full-text search across all patterns and compositions |
| `debug_record` | Record a completed debugging trajectory to memory |
| `debug_score` | Score a trajectory against the 6-criterion rubric (100 points) |
| `debug_dap_commands` | Generate DAP commands from a pattern's debugger strategy |

## Examples

### Classify a symptom

```
Tool: debug_classify
Args: { "symptom": "transfer connects to wrong department after config change" }

→ Confidence: high
  #1 P08 (score: 4)
  #2 P07 (score: 2)
```

### Get DAP commands for a pattern

```
Tool: debug_dap_commands
Args: { "pattern_id": "P02", "file_path": "src/transcript_manager.py" }

→ {
    "pattern": "P02",
    "strategy": {
      "breakpoints": ["context_manager.save — Conditional: if field == \"transcript\"", ...],
      "watch_expressions": ["db.transcript — Snapshot before/after each write", ...]
    },
    "dap_commands": [...]
  }
```

### Score a trajectory

```
Tool: debug_score
Args: { "pattern_check": 15, "reproduction": 15, "hypothesis_quality": 18, "isolation": 17, "root_cause_depth": 15, "fix_minimality": 14 }

→ Total: 94/100 (A+)
```

## Architecture

```
mcp-server/
├── src/debug_bank_mcp/
│   ├── server.py              # MCP server entry point
│   ├── tools/
│   │   ├── classify.py        # Symptom → pattern classifier
│   │   ├── pattern.py         # Pattern lookup by ID
│   │   ├── search.py          # Full-text pattern search
│   │   ├── record.py          # Trajectory recording
│   │   └── score.py           # Trajectory scoring
│   ├── bridge/
│   │   └── dap_bridge.py      # DAP command generator
│   └── memory/
│       └── trajectory_store.py # JSON-file trajectory persistence
└── README.md
```

## Requirements

- Python ≥ 3.10
- `mcp` SDK ≥ 1.0.0
- `pyyaml` ≥ 6.0
- Optional: `debugpy` for DAP integration
