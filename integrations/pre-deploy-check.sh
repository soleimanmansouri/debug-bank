#!/usr/bin/env bash
# =============================================================================
# Debug Bank Pre-Deploy Check
# =============================================================================
#
# Scans a git diff for changed handlers and matches against debug-bank patterns
# to catch known anti-patterns BEFORE they ship.
#
# Usage:
#   bash pre-deploy-check.sh                    # checks origin/main..HEAD
#   bash pre-deploy-check.sh main..feature      # checks specific range
#   bash pre-deploy-check.sh HEAD~3..HEAD       # checks last 3 commits
#
# Exit codes:
#   0 — no issues found (or informational only)
#   1 — patterns flagged, review recommended before deploy
#
# Dependencies: bash, git, grep (no external tools required)
# =============================================================================

set -euo pipefail

# --- Configuration -----------------------------------------------------------

DIFF_RANGE="${1:-origin/main..HEAD}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PATTERNS_DIR="$(cd "$SCRIPT_DIR/../patterns" && pwd)"

# Colors (disabled if not a terminal)
if [ -t 1 ]; then
    RED='\033[0;31m'
    YELLOW='\033[1;33m'
    GREEN='\033[0;32m'
    BLUE='\033[0;34m'
    BOLD='\033[1m'
    NC='\033[0m'
else
    RED='' YELLOW='' GREEN='' BLUE='' BOLD='' NC=''
fi

# --- Pattern keyword map -----------------------------------------------------
# Format: "PATTERN_ID:keyword1,keyword2,keyword3"
# Each keyword triggers a flag if found in the diff.

PATTERN_KEYWORDS=(
    "P01:super().__init__,default_kwargs,wrapper_defaults"
    "P02:queue_frame,write_frame,multiple_writers,transcript_write"
    "P03:on_frame,observer,add_observer,register_handler"
    "P04:example_response,sample_output,example_output"
    "P05:skip_processing,enable_flag,disable_flag,is_enabled"
    "P06:requirements.txt,poetry.lock,package-lock,pip install"
    "P07:config_path,settings_path,yaml_path,stale_config"
    "P08:fallback_config,default_config,config_chain"
    "P09:auto_apply,pipeline_feedback,auto_save"
    "P10:model_name,provider_config,api_key,voice_id"
    "P11:credential_expression,env_expression"
    "P12:expression_engine,non_json_body,content_type"
    "P13:parse_response,error_indicator,status_code"
    "P14:expression_prefix,template_literal"
    "P15:multi_output,split_output"
    "P16:binary_data,file_data,buffer_data"
    "P17:context_message,system_prompt_content,conversation_history"
    "P18:CancelFrame,EndFrame,end_conversation,disconnect,timeout,debounce"
    "P19:prompt_engineering,system_prompt,few_shot"
    "P20:filler,background_audio,hold_music,queue_frame,start_filler,stop_filler"
    "P21:handle_,handler,shared_code,decorator,base_class"
)

# --- Functions ---------------------------------------------------------------

print_header() {
    echo ""
    echo -e "${BOLD}========================================${NC}"
    echo -e "${BOLD}  Debug Bank Pre-Deploy Check${NC}"
    echo -e "${BOLD}========================================${NC}"
    echo -e "  Range: ${BLUE}${DIFF_RANGE}${NC}"
    echo ""
}

print_section() {
    echo -e "${BOLD}--- $1 ---${NC}"
}

get_changed_python_files() {
    git diff --name-only --diff-filter=ACMR "$DIFF_RANGE" -- '*.py' 2>/dev/null || true
}

get_diff_content() {
    git diff "$DIFF_RANGE" -- '*.py' 2>/dev/null || true
}

find_changed_handlers() {
    local diff_content="$1"
    # Look for added/modified lines containing handler function definitions
    echo "$diff_content" | grep -E '^\+.*async def handle_' | sed 's/^+[[:space:]]*//' | sed 's/(.*//;s/async def //' | sort -u || true
}

find_all_handlers_in_changed_files() {
    local changed_files="$1"
    local handlers=""
    while IFS= read -r file; do
        [ -z "$file" ] && continue
        if [ -f "$file" ]; then
            local file_handlers
            file_handlers=$(grep -n 'async def handle_' "$file" 2>/dev/null | sed 's/.*async def //;s/(.*//') || true
            if [ -n "$file_handlers" ]; then
                while IFS= read -r h; do
                    handlers="${handlers}${h} (${file})"$'\n'
                done <<< "$file_handlers"
            fi
        fi
    done <<< "$changed_files"
    echo "$handlers"
}

check_patterns() {
    local diff_content="$1"
    local flagged_count=0
    local flagged_patterns=""

    for entry in "${PATTERN_KEYWORDS[@]}"; do
        local pattern_id="${entry%%:*}"
        local keywords_str="${entry#*:}"
        IFS=',' read -ra keywords <<< "$keywords_str"

        local matched_keywords=""
        for kw in "${keywords[@]}"; do
            if echo "$diff_content" | grep -qi "$kw" 2>/dev/null; then
                if [ -z "$matched_keywords" ]; then
                    matched_keywords="$kw"
                else
                    matched_keywords="$matched_keywords, $kw"
                fi
            fi
        done

        if [ -n "$matched_keywords" ]; then
            # Get pattern name from file
            local pattern_file
            pattern_file=$(ls "$PATTERNS_DIR"/${pattern_id}-*.md 2>/dev/null | head -1)
            local pattern_name="$pattern_id"
            if [ -n "$pattern_file" ] && [ -f "$pattern_file" ]; then
                pattern_name=$(grep "^# ${pattern_id}:" "$pattern_file" 2>/dev/null | sed "s/^# //" || echo "$pattern_id")
            fi

            flagged_patterns="${flagged_patterns}  ${YELLOW}[${pattern_id}]${NC} ${pattern_name}\n"
            flagged_patterns="${flagged_patterns}         Matched: ${matched_keywords}\n"
            flagged_count=$((flagged_count + 1))
        fi
    done

    echo "$flagged_count"
    echo -e "$flagged_patterns"
}

# --- Main --------------------------------------------------------------------

main() {
    print_header

    # Check we're in a git repo
    if ! git rev-parse --is-inside-work-tree &>/dev/null; then
        echo -e "${RED}Error: Not inside a git repository.${NC}"
        exit 1
    fi

    # Check if diff range is valid
    if ! git rev-parse "$DIFF_RANGE" &>/dev/null 2>&1; then
        # Try to handle the case where origin/main doesn't exist
        if [ "$DIFF_RANGE" = "origin/main..HEAD" ]; then
            # Fall back to main..HEAD or just HEAD
            if git rev-parse main &>/dev/null 2>&1; then
                DIFF_RANGE="main..HEAD"
            else
                echo -e "${YELLOW}Warning: Could not resolve diff range. Checking HEAD~1..HEAD${NC}"
                DIFF_RANGE="HEAD~1..HEAD"
            fi
        else
            echo -e "${RED}Error: Invalid diff range '${DIFF_RANGE}'${NC}"
            exit 1
        fi
    fi

    # 1. Get changed Python files
    print_section "Changed Python Files"
    local changed_files
    changed_files=$(get_changed_python_files)
    if [ -z "$changed_files" ]; then
        echo -e "  ${GREEN}No Python files changed in ${DIFF_RANGE}${NC}"
        echo ""
        echo -e "${GREEN}Result: Nothing to check. Safe to deploy.${NC}"
        exit 0
    fi
    local file_count
    file_count=$(echo "$changed_files" | wc -l | tr -d ' ')
    echo "  $file_count Python file(s) changed:"
    echo "$changed_files" | while read -r f; do echo "    - $f"; done
    echo ""

    # 2. Get full diff content
    local diff_content
    diff_content=$(get_diff_content)

    # 3. Find changed handlers
    print_section "Changed Handlers"
    local changed_handlers
    changed_handlers=$(find_changed_handlers "$diff_content")
    local all_handlers
    all_handlers=$(find_all_handlers_in_changed_files "$changed_files")

    local handler_count=0
    local directly_modified=0
    if [ -n "$changed_handlers" ]; then
        directly_modified=$(echo "$changed_handlers" | grep -c . || true)
        echo "  $directly_modified handler(s) directly modified:"
        echo "$changed_handlers" | while read -r h; do echo "    - $h"; done
    fi

    if [ -n "$all_handlers" ]; then
        handler_count=$(echo "$all_handlers" | grep -c . || true)
        echo ""
        echo "  $handler_count handler(s) in changed files (all need testing):"
        echo "$all_handlers" | while read -r h; do
            [ -n "$h" ] && echo "    - $h"
        done
    fi

    if [ -z "$changed_handlers" ] && [ -z "$all_handlers" ]; then
        echo -e "  ${GREEN}No handler functions found in changed files.${NC}"
    fi
    echo ""

    # 4. Print handler test checklist
    if [ -n "$all_handlers" ]; then
        print_section "Handler Test Checklist"
        echo "$all_handlers" | while read -r h; do
            [ -z "$h" ] && continue
            local name="${h%% (*}"
            echo -e "  ${YELLOW}[ ]${NC} Test call through ${BOLD}${name}${NC} path"
            echo -e "  ${YELLOW}[ ]${NC} Verify no filler/frame contention in ${name} (P20)"
            echo -e "  ${YELLOW}[ ]${NC} Check for multiple writers to same pipeline queue in ${name} (P02)"
            echo ""
        done
    fi

    # 5. Check patterns against diff
    print_section "Pattern Scan"
    local pattern_result
    pattern_result=$(check_patterns "$diff_content")
    local flagged_count
    flagged_count=$(echo "$pattern_result" | head -1)
    local flagged_details
    flagged_details=$(echo "$pattern_result" | tail -n +2)

    if [ "$flagged_count" -gt 0 ] 2>/dev/null; then
        echo -e "  ${YELLOW}${flagged_count} pattern(s) flagged:${NC}"
        echo ""
        echo -e "$flagged_details"
    else
        echo -e "  ${GREEN}No patterns flagged.${NC}"
    fi
    echo ""

    # 6. Summary
    echo -e "${BOLD}========================================${NC}"
    echo -e "${BOLD}  Summary${NC}"
    echo -e "${BOLD}========================================${NC}"
    echo -e "  Files changed:    ${file_count}"
    echo -e "  Handlers found:   ${handler_count:-0}"
    echo -e "  Patterns flagged: ${flagged_count:-0}"
    echo ""

    if [ "${flagged_count:-0}" -gt 0 ] 2>/dev/null || [ "${handler_count:-0}" -gt 0 ] 2>/dev/null; then
        echo -e "  ${YELLOW}${file_count} file(s) changed, ${handler_count:-0} handler(s) found, ${flagged_count:-0} pattern(s) flagged${NC}"
        echo -e "  ${YELLOW}Review checklist above before deploying.${NC}"
        echo ""
        exit 1
    else
        echo -e "  ${GREEN}No handlers or patterns flagged. Proceed with deploy.${NC}"
        echo ""
        exit 0
    fi
}

main
