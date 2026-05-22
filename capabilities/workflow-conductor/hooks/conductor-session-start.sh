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
请参照 Session Objective Protocol 执行发现与绑定流程。绑定后请立即读取完整协议 conductor-protocol.md。"

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
  printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":%s}}\n' "$escaped_ctx"
else
  printf '{"additional_context":%s}\n' "$escaped_ctx"
fi
