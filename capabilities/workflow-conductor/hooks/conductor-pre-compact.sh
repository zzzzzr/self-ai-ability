#!/usr/bin/env bash
# conductor-pre-compact.sh — PreCompact hook for workflow-conductor
# Before context compaction, injects the full active objective content into context
# so that key constraints and progress survive the compression.
# Works on both Claude Code (additionalContext) and Cursor (user_message).
set -euo pipefail

INPUT=$(cat)

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
OBJ_DIR="${PROJECT_DIR}/.ai-objectives"

if [[ ! -d "$OBJ_DIR" ]]; then
  exit 0
fi

active_file=""
for f in "$OBJ_DIR"/*.md; do
  [[ -f "$f" ]] || continue
  if head -10 "$f" | grep -q 'status:[[:space:]]*active'; then
    active_file="$f"
    break
  fi
done

if [[ -z "$active_file" ]]; then
  exit 0
fi

fname=$(basename "$active_file")
file_content=$(cat "$active_file")

context="[Conductor] Context 即将被压缩。以下是当前活跃 objective 文件 (${fname}) 的完整内容，请确保压缩后仍保留这些信息：

${file_content}"

is_claude_code=false
if echo "$INPUT" | grep -q '"hook_event_name"' 2>/dev/null; then
  is_claude_code=true
fi

json_escape() {
  if command -v jq &>/dev/null; then
    jq -Rs '.' <<< "$1"
  else
    python3 -c "import json,sys; print(json.dumps(sys.stdin.read()))" <<< "$1"
  fi
}

escaped_ctx=$(json_escape "$context")

if [[ "$is_claude_code" == true ]]; then
  printf '{"hookSpecificOutput":{"hookEventName":"PreCompact","additionalContext":%s}}\n' "$escaped_ctx"
else
  printf '{"user_message":%s}\n' "$escaped_ctx"
fi
