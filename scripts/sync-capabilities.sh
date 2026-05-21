#!/usr/bin/env bash
# sync-capabilities.sh — 对多个目标项目批量执行同一条安装命令
# 命令中用 {dest} 占位符代表目标路径，脚本会逐个替换并执行
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/sync-config.json"

usage() {
  cat <<EOF
Usage: sync-capabilities.sh <command with {dest} placeholder>

对配置文件中的每个目标项目执行指定命令。
命令中的 {dest} 会被替换为目标项目路径。

Config: $CONFIG_FILE

Examples:
  sync-capabilities.sh "python3 scripts/install-cursor-capability.py workflow-conductor --dest {dest} --force"
  sync-capabilities.sh "cp some-rule.mdc {dest}/.cursor/rules/"
  sync-capabilities.sh "bash ~/other-repo/install.sh --project={dest}"
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
