# Integration: Claude Code

## Quick Setup

### Option 1: Drop-in CLAUDE.md

Copy the project's `CLAUDE.md` to your project root:

```bash
cp CLAUDE.md /path/to/your/project/
```

This activates the debug trajectory protocol for all Claude Code sessions in that project.

### Option 2: Install Skills

```bash
# Copy skills to your Claude Code skills directory
cp -r skills/debug-trajectory ~/.claude/skills/
cp -r skills/pattern-check ~/.claude/skills/
```

Skills are invoked automatically when debugging, or manually via `/debug-trajectory` and `/pattern-check`.

### Option 3: Global CLAUDE.md

To apply the protocol across all projects, add the protocol to your global CLAUDE.md:

```bash
# Append to global instructions
cat CLAUDE.md >> ~/.claude/CLAUDE.md
```

## Setting Up Your Pattern Bank

1. Copy the starter patterns to your project:
   ```bash
   cp -r patterns/ /path/to/your/project/patterns/
   ```

2. Create your first domain catalog:
   ```bash
   mkdir -p /path/to/your/project/debug-memory/
   cp examples/voice-pipeline/catalog.md /path/to/your/project/debug-memory/
   ```
   
   Rename and customize the catalog for your domain.

3. Start debugging — every fix gets recorded, patterns compound.

## Setting Up Feedback Rules

Create a `debug-memory/feedback/` directory in your project:

```bash
mkdir -p /path/to/your/project/debug-memory/feedback/
```

When Claude Code captures a feedback rule, it saves it there. Rules are loaded at session start.

## How It Works in Practice

1. You report a bug: "The API returns 404 after switching environments"
2. Claude Code activates the debug-trajectory skill
3. Step 1 (Pattern Check): Scans P01-P19 → finds P07 (Stale Config) and P08 (Config Chain Gap)
4. Checks P08's checklist → confirms: environment switch didn't update the base URL cache
5. Applies fix → records trajectory in your domain catalog
6. Next time a similar bug appears, the pattern check resolves it in 30 seconds

## Recommended Project Structure

```
your-project/
├── CLAUDE.md                  # Includes debug trajectory protocol
├── patterns/                  # Pattern bank (start with P01-P19)
│   ├── P01-wrapper-defaults.md
│   └── ...
├── debug-memory/
│   ├── catalogs/
│   │   ├── backend.md         # Your domain catalogs
│   │   └── frontend.md
│   └── feedback/
│       ├── no-db-mocks.md     # Your feedback rules
│       └── autonomous-testing.md
└── ...your code...
```
