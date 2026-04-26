# Integration: Cursor

## Setup

Cursor uses `.cursorrules` for project-level instructions.

### Step 1: Add Protocol

Append the contents of `CLAUDE.md` to your `.cursorrules` file:

```bash
cat CLAUDE.md >> /path/to/your/project/.cursorrules
```

Or if you don't have a `.cursorrules` file yet:

```bash
cp CLAUDE.md /path/to/your/project/.cursorrules
```

### Step 2: Add Pattern Bank

```bash
cp -r patterns/ /path/to/your/project/patterns/
```

### Step 3: Create Domain Catalogs

```bash
mkdir -p /path/to/your/project/debug-memory/catalogs/
```

## Cursor-Specific Notes

- Cursor loads `.cursorrules` at the start of every session
- Pattern files in `patterns/` are accessible via Cursor's file reading capabilities
- For Cursor's Composer mode, the debug trajectory protocol helps structure multi-step debugging

## Limitations

- Cursor doesn't support skills (`SKILL.md`). Use the `.cursorrules` drop-in instead.
- Feedback rules need to be manually added to `.cursorrules` or a referenced file.
- Pattern check requires Cursor to read files from the `patterns/` directory — ensure they're not in `.cursorignore`.

## Recommended `.cursorrules` Addition

At minimum, add this to your `.cursorrules`:

```
## Debugging Protocol

When debugging, always check patterns/ directory first for matching root cause types.
Follow: Pattern Check → Reproduce → Hypothesize → Isolate → Diagnose → Fix → Record.
Stop after 3 failed attempts and switch strategy.
```
