# Integration: OpenAI Codex CLI

## Setup

Codex CLI reads `AGENTS.md` from your project root.

### Step 1: Add Protocol

Copy `AGENTS.md` to your project root:

```bash
cp AGENTS.md /path/to/your/project/
```

### Step 2: Add Pattern Bank

```bash
cp -r patterns/ /path/to/your/project/patterns/
```

### Step 3: Create Domain Catalogs

```bash
mkdir -p /path/to/your/project/debug-memory/catalogs/
```

Create catalog files following the format in `memory/domain-catalogs.md`.

## How It Works

Codex CLI reads `AGENTS.md` at session start and follows the debug trajectory protocol when debugging. The protocol is agent-agnostic — the same patterns and catalogs work regardless of the underlying model.

## Notes

- Codex CLI may not support skills (`SKILL.md`). Use the `AGENTS.md` drop-in instead.
- Pattern files are plain markdown — readable by any agent.
- Domain catalogs and feedback rules work the same as in Claude Code.
