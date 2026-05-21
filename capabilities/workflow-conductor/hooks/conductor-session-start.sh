#!/usr/bin/env bash
# conductor-session-start.sh — SessionStart hook for workflow-conductor
# Scans .ai-objectives/ for active objectives and injects summary into agent context.
# Works on both Claude Code (additionalContext) and Cursor (additional_context).
set -euo pipefail

INPUT=$(cat)

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
OBJ_DIR="${PROJECT_DIR}/.ai-objectives"

if [[ ! -d "$OBJ_DIR" ]]; then
  exit 0
fi

active_files=()
summaries=()

for f in "$OBJ_DIR"/*.md; do
  [[ -f "$f" ]] || continue

  status=""
  objective=""
  created=""
  in_frontmatter=0

  while IFS= read -r line; do
    if [[ "$line" == "---" ]]; then
      if [[ $in_frontmatter -eq 1 ]]; then
        break
      fi
      in_frontmatter=1
      continue
    fi
    if [[ $in_frontmatter -eq 1 ]]; then
      case "$line" in
        status:*)  status="${line#status:}"; status="${status## }" ;;
        objective:*) objective="${line#objective:}"; objective="${objective## }" ;;
        created:*) created="${line#created:}"; created="${created## }" ;;
      esac
    fi
  done < "$f"

  if [[ "$status" == "active" ]]; then
    fname=$(basename "$f")
    active_files+=("$fname")
    summaries+=("- ${fname}: ${objective} (created: ${created})")
  fi
done

if [[ ${#active_files[@]} -eq 0 ]]; then
  exit 0
fi

count=${#active_files[@]}
context="[Conductor] 发现 ${count} 个活跃目标文件："
for s in "${summaries[@]}"; do
  context="${context}
${s}"
done
context="${context}
请参照 Session Objective Protocol 执行发现与绑定流程。"

is_claude_code=false
if echo "$INPUT" | grep -q '"hook_event_name"' 2>/dev/null; then
  is_claude_code=true
fi

if [[ "$is_claude_code" == true ]]; then
  if command -v jq &>/dev/null; then
    jq -n --arg ctx "$context" '{
      hookSpecificOutput: {
        hookEventName: "SessionStart",
        additionalContext: $ctx
      }
    }'
  else
    escaped=$(echo "$context" | sed 's/\\/\\\\/g; s/"/\\"/g' | tr '\n' '\\' | sed 's/\\/\\n/g')
    cat <<EOJSON
{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"${escaped}"}}
EOJSON
  fi
else
  if command -v jq &>/dev/null; then
    jq -n --arg ctx "$context" '{ additional_context: $ctx }'
  else
    escaped=$(echo "$context" | sed 's/\\/\\\\/g; s/"/\\"/g' | tr '\n' '\\' | sed 's/\\/\\n/g')
    cat <<EOJSON
{"additional_context":"${escaped}"}
EOJSON
  fi
fi
