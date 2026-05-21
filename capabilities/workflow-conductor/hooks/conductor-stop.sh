#!/usr/bin/env bash
# conductor-stop.sh — Stop hook for workflow-conductor (Claude Code only)
# After each agent response, reads active objective file and injects a reminder
# into context so the agent stays aware of current progress and pending steps.
set -euo pipefail

INPUT=$(cat)

# Avoid infinite loop: if stop hook is already active, skip
if echo "$INPUT" | grep -q '"stop_hook_active"[[:space:]]*:[[:space:]]*true' 2>/dev/null; then
  exit 0
fi

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

total=0
done_count=0
pending_lines=""
while IFS= read -r line; do
  if [[ "$line" =~ ^[[:space:]]*-[[:space:]]\[.\] ]]; then
    total=$((total + 1))
    if [[ "$line" =~ ^[[:space:]]*-[[:space:]]\[x\] ]]; then
      done_count=$((done_count + 1))
    else
      pending_lines="${pending_lines}
  ${line}"
    fi
  fi
done < "$active_file"

pending=$((total - done_count))

if [[ $total -eq 0 ]]; then
  exit 0
fi

context="[Conductor] 当前绑定: ${fname} (${done_count}/${total} 完成, ${pending} 待完成)"
if [[ $pending -gt 0 ]]; then
  context="${context}
未完成步骤:${pending_lines}"
fi
context="${context}
如果刚完成了某个步骤，请检查是否需要更新 objective 文件（勾选 checkbox、追加约束等）。"

if command -v jq &>/dev/null; then
  jq -n --arg ctx "$context" '{
    hookSpecificOutput: {
      hookEventName: "Stop",
      additionalContext: $ctx
    }
  }'
else
  escaped=$(echo "$context" | sed 's/\\/\\\\/g; s/"/\\"/g' | tr '\n' '\\' | sed 's/\\/\\n/g')
  cat <<EOJSON
{"hookSpecificOutput":{"hookEventName":"Stop","additionalContext":"${escaped}"}}
EOJSON
fi
