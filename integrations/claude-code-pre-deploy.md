# Integration: Claude Code Pre-Deploy Check

Automatically catch known anti-patterns before deploying voice pipeline changes. This integration runs the debug-bank pattern scanner against your git diff and flags matches before code ships.

## Quick Setup

### Step 1: Add to Your Project's CLAUDE.md

Add this block to the `CLAUDE.md` in your voice pipeline project (e.g., `~/Cara8/02_Voice_Pipeline/CLAUDE.md`):

```markdown
## Pre-Deploy Protocol
Before deploying to Fly.io:
1. Run `bash ~/Cara8/debug-bank/integrations/pre-deploy-check.sh`
2. For each flagged pattern, verify the fix doesn't match the anti-pattern
3. For each changed handler, make a test call through that specific path
4. Only deploy after all checklist items are verified
```

This ensures Claude Code (and any developer reading the project instructions) follows the pre-deploy checklist.

### Step 2: Add Claude Code Hook (Automatic)

Add this to your project's `.claude/settings.json` (create the file if it doesn't exist):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "if echo \"$TOOL_INPUT\" | grep -q 'fly deploy'; then bash ~/Cara8/debug-bank/integrations/pre-deploy-check.sh 2>&1 | head -80; fi"
          }
        ]
      }
    ]
  }
}
```

This hook runs automatically whenever Claude Code is about to execute a `fly deploy` command. The pre-deploy check output appears in the hook context, so Claude Code sees any flagged patterns before proceeding.

### Step 3: Verify the Setup

Test that the hook works by running the check manually:

```bash
cd ~/Cara8/02_Voice_Pipeline
bash ~/Cara8/debug-bank/integrations/pre-deploy-check.sh
```

You should see output listing changed files, handlers, and any pattern matches.

## How It Works

1. **File scan** — The script runs `git diff origin/main..HEAD` to find changed Python files
2. **Handler detection** — It greps for `async def handle_` to identify modified handler functions
3. **Pattern matching** — Each of the 21 debug-bank patterns has associated keywords. The script checks if any keyword appears in the diff
4. **Checklist generation** — For each changed handler, it prints a test checklist (test the path, check P20 filler contention, check P02 multiple writers)
5. **Exit code** — Returns 1 if any patterns are flagged or handlers need testing, 0 if clean

## Manual Usage

```bash
# Default: check origin/main..HEAD
bash ~/Cara8/debug-bank/integrations/pre-deploy-check.sh

# Check a specific range
bash ~/Cara8/debug-bank/integrations/pre-deploy-check.sh main..feature-branch

# Check last 3 commits
bash ~/Cara8/debug-bank/integrations/pre-deploy-check.sh HEAD~3..HEAD
```

## What Gets Checked

The script matches diff content against keywords for all 21 patterns:

| Pattern | Trigger Keywords |
|---------|-----------------|
| P02 | `queue_frame`, `write_frame`, `multiple_writers` |
| P18 | `CancelFrame`, `EndFrame`, `end_conversation`, `timeout` |
| P20 | `filler`, `background_audio`, `hold_music`, `start_filler`, `stop_filler` |
| P21 | `handle_`, `handler`, `shared_code`, `decorator` |
| ... | See script source for full keyword list |

## Extending

To add keywords for a new pattern:

1. Open `integrations/pre-deploy-check.sh`
2. Find the `PATTERN_KEYWORDS` array
3. Add a new line: `"PXX:keyword1,keyword2,keyword3"`
4. Keywords are matched case-insensitively against the full diff output

## Troubleshooting

**"Not inside a git repository"** — Run the script from inside your project directory.

**"Could not resolve diff range"** — The default range `origin/main..HEAD` requires a remote named `origin` with a `main` branch. Pass a custom range: `bash pre-deploy-check.sh HEAD~5..HEAD`.

**No output / no files** — If there are no Python file changes in the diff range, the script exits cleanly with "Nothing to check."
