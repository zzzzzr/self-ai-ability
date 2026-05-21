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

if [[ "$is_claude_code" == true ]]; then
  if command -v jq &>/dev/null; then
    jq -n --arg ctx "$context" '{
      hookSpecificOutput: {
        hookEventName: "PreCompact",
        additionalContext: $ctx
      }
    }'
  else
    escaped=$(echo "$context" | sed 's/\\/\\\\/g; s/"/\\"/g' | tr '\n' '\\' | sed 's/\\/\\n/g')
    cat <<EOJSON
{"hookSpecificOutput":{"hookEventName":"PreCompact","additionalContext":"${escaped}"}}
EOJSON
  fi
else
  if command -v jq &>/dev/null; then
    jq -n --arg ctx "$context" '{ user_message: $ctx }'
  else
    escaped=$(echo "$context" | sed 's/\\/\\\\/g; s/"/\\"/g' | tr '\n' '\\' | sed 's/\\/\\n/g')
    cat <<EOJSON
{"user_message":"${escaped}"}
EOJSON
  fi
fi
