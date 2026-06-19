#!/usr/bin/env bash
# run-command.sh — 对多个目标项目批量执行同一条命令（{dest} 占位符）
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CAPABILITY_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG_FILE="$CAPABILITY_DIR/config/sync-config.json"

usage() {
  cat <<EOF
Usage: run-command.sh <command with {dest} placeholder>

对配置文件中的每个目标项目执行指定命令。
命令中的 {dest} 会被替换为目标项目路径。

Config: $CONFIG_FILE

Examples:
  run-command.sh "./install.sh workflow-conductor --dest {dest} --force"
  run-command.sh "cp some-rule.mdc {dest}/.cursor/rules/"
  run-command.sh "bash ~/other-repo/install.sh --project={dest}"
EOF
  exit 0
}

if [[ $# -eq 0 || "$1" == "--help" ]]; then
  usage
fi

COMMAND="$*"

if [[ ! -f "$CONFIG_FILE" ]]; then
  echo "ERROR: 配置文件不存在: $CONFIG_FILE" >&2
  exit 1
fi

if [[ "$COMMAND" != *"{dest}"* ]]; then
  echo "ERROR: 命令中必须包含 {dest} 占位符" >&2
  exit 1
fi

TARGETS=$(python3 -c "
import json, os, sys
d = json.load(open('$CONFIG_FILE'))
for t in d.get('targets', []):
    print(os.path.expanduser(t))
")

TOTAL=0
SUCCESS=0
FAIL=0

while IFS= read -r target; do
  [[ -z "$target" ]] && continue
  TOTAL=$((TOTAL + 1))

  cmd="${COMMAND//\{dest\}/$target}"

  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "[$TOTAL] $target"
  echo "  → $cmd"
  echo ""

  if eval "$cmd"; then
    SUCCESS=$((SUCCESS + 1))
  else
    FAIL=$((FAIL + 1))
    echo "  ⚠ FAILED"
  fi
  echo ""
done <<< "$TARGETS"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Done. total=$TOTAL success=$SUCCESS fail=$FAIL"
