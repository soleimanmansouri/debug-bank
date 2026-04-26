# Integration: Google Gemini CLI

## Setup

Gemini CLI reads `AGENTS.md` from your project root.

### Step 1: Add Protocol

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

## Gemini-Specific Notes

- Gemini CLI supports the `AGENTS.md` format natively
- Pattern files are loaded on demand when the debug protocol is activated
- For Gemini CLI with skill support, place skills in `.gemini/skills/` instead of `.claude/skills/`

## How It Works

Same protocol, same patterns, same catalogs. The debug trajectory protocol is model-agnostic — it works because it structures the debugging process, not because it relies on any model-specific behavior.
