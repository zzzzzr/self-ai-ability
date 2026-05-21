#!/usr/bin/env bash
# install.sh — 将 Session Objective Protocol 安装到 ~/.claude/CLAUDE.md，并注册 hooks
# 从 rules/session-objective.md 读取（单一源文件），写入时自动剥离 YAML frontmatter
# 幂等：重复执行不会重复写入；--force 强制替换已有内容
# 用成对 HTML 注释标记包裹内容，--force 按标记范围删除，不影响其他内容
# Hooks: 复制 hook 脚本到 ~/.claude/hooks/，并注册到 ~/.claude/settings.json

set -euo pipefail

usage() {
  cat <<EOF
Usage: install.sh [OPTIONS]

将 Session Objective Protocol 安装到 ~/.claude/CLAUDE.md

Options:
  --force              强制替换已有的 Session Objective Protocol 内容
  --project=<path>     指定项目目录，用于追加 .ai-objectives/ 到该项目的 .gitignore
                       默认为当前工作目录
  --help               显示此帮助信息

Examples:
  install.sh                          # 首次安装
  install.sh --force                  # 强制更新
  install.sh --project=/path/to/repo  # 指定项目目录
  install.sh --force --project=.      # 强制更新 + 当前目录
EOF
  exit 0
}

FORCE=false
PROJECT_DIR="."

for arg in "$@"; do
  case "$arg" in
    --force)
      FORCE=true
      ;;
    --project=*)
      PROJECT_DIR="${arg#--project=}"
      ;;
    --help)
      usage
      ;;
    *)
      echo "ERROR: 未知参数: $arg" >&2
      echo "使用 --help 查看帮助" >&2
      exit 1
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CAP_ROOT="${SCRIPT_DIR}/.."
RULE_FILE="${CAP_ROOT}/rules/session-objective.md"
HOOKS_SRC_DIR="${CAP_ROOT}/hooks"
CLAUDE_DIR="${HOME}/.claude"
CLAUDE_MD="${CLAUDE_DIR}/CLAUDE.md"
CLAUDE_SETTINGS="${CLAUDE_DIR}/settings.json"
HOOKS_DST_DIR="${CLAUDE_DIR}/hooks"

START_MARKER="<!-- workflow-conductor:start -->"
END_MARKER="<!-- workflow-conductor:end -->"

# 检查源文件存在
if [[ ! -f "${RULE_FILE}" ]]; then
  echo "ERROR: 源文件不存在: ${RULE_FILE}" >&2
  exit 1
fi

# 确保 ~/.claude 目录存在
mkdir -p "${CLAUDE_DIR}"

# 幂等检查：如果已包含成对标记
ALREADY_INSTALLED=false
if [[ -f "${CLAUDE_MD}" ]] && grep -qF "${START_MARKER}" "${CLAUDE_MD}"; then
  ALREADY_INSTALLED=true
  if [[ "${FORCE}" == false ]]; then
    echo "Session Objective Protocol 已存在于 ${CLAUDE_MD}，跳过写入。"
    echo "如需更新，请使用 --force 参数强制替换。"
    exit 0
  fi
fi

# 剥离 YAML frontmatter 的函数
strip_frontmatter() {
  awk '
    BEGIN { in_front=0 }
    NR==1 && /^---/ { in_front=1; next }
    in_front && /^---/ { in_front=0; next }
    !in_front { print }
  ' "$1"
}

# 组装内容：用成对标记包裹
CONTENT="${START_MARKER}
$(strip_frontmatter "${RULE_FILE}")
${END_MARKER}"

# 写入 CLAUDE.md
if [[ "${ALREADY_INSTALLED}" == true ]]; then
  # --force 原地替换：在 start marker 位置插入新内容，跳过旧内容
  # 使用 trim 后匹配，容忍行首尾空白（防止用户手动编辑引入空格）
  CONTENT_TMP="$(mktemp)"
  printf '%s\n' "${CONTENT}" > "${CONTENT_TMP}"
  awk -v sm="${START_MARKER}" -v em="${END_MARKER}" -v newfile="${CONTENT_TMP}" '
    function trim(s) { gsub(/^[ \t]+|[ \t]+$/, "", s); return s }
    trim($0) == sm {
      while ((getline line < newfile) > 0) print line
      close(newfile)
      skip=1; next
    }
    trim($0) == em { skip=0; next }
    !skip { print }
  ' "${CLAUDE_MD}" > "${CLAUDE_MD}.tmp"
  rm -f "${CONTENT_TMP}"
  mv "${CLAUDE_MD}.tmp" "${CLAUDE_MD}"
  echo "已原地替换 Session Objective Protocol（${CLAUDE_MD}）"
elif [[ -f "${CLAUDE_MD}" ]]; then
  # 首次安装，文件已存在：追加到末尾
  printf '\n%s\n' "${CONTENT}" >> "${CLAUDE_MD}"
  echo "已追加 Session Objective Protocol 到 ${CLAUDE_MD}"
else
  # 文件不存在：创建新文件
  {
    echo "# Global Instructions"
    echo ""
    echo "${CONTENT}"
  } > "${CLAUDE_MD}"
  echo "已创建 ${CLAUDE_MD} 并写入 Session Objective Protocol"
fi

# 尝试将 .ai-objectives/ 追加到项目的 .gitignore
# 仅在 .gitignore 已存在时追加；不主动创建——因为本脚本默认安装到 ~/.claude/（全局），
# 项目级的 .gitignore 应由协议运行时自动处理（见 session-objective.md 创建流程步骤 4）
GITIGNORE="${PROJECT_DIR}/.gitignore"
IGNORE_ENTRY=".ai-objectives/"

if [[ -f "${GITIGNORE}" ]]; then
  if ! grep -qxF "${IGNORE_ENTRY}" "${GITIGNORE}"; then
    printf '\n%s\n' "${IGNORE_ENTRY}" >> "${GITIGNORE}"
    echo "已追加 ${IGNORE_ENTRY} 到 ${GITIGNORE}"
  else
    echo "${IGNORE_ENTRY} 已存在于 ${GITIGNORE}，跳过。"
  fi
else
  echo "提示：未找到 ${GITIGNORE}，请手动将 ${IGNORE_ENTRY} 添加到项目的 .gitignore 中。"
fi

# ── Hooks 安装 ──────────────────────────────────────────────────────────────

HOOK_SCRIPTS=(
  "conductor-session-start.sh"
  "conductor-stop.sh"
  "conductor-pre-compact.sh"
)

mkdir -p "${HOOKS_DST_DIR}"
for script in "${HOOK_SCRIPTS[@]}"; do
  src="${HOOKS_SRC_DIR}/${script}"
  dst="${HOOKS_DST_DIR}/${script}"
  if [[ ! -f "$src" ]]; then
    echo "WARN: hook 脚本不存在: ${src}" >&2
    continue
  fi
  if [[ -f "$dst" ]] && [[ "${FORCE}" == false ]]; then
    echo "hook 脚本已存在: ${dst}，跳过。使用 --force 覆盖。"
  else
    cp "$src" "$dst"
    chmod +x "$dst"
    echo "已安装 hook 脚本: ${dst}"
  fi
done

# 注册 hooks 到 settings.json（幂等：检查是否已存在 conductor 相关 hook）
HOOKS_JSON='{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "'"${HOOKS_DST_DIR}"'/conductor-session-start.sh"
          }
        ]
      }
    ],
    "Stop": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "'"${HOOKS_DST_DIR}"'/conductor-stop.sh"
          }
        ]
      }
    ],
    "PreCompact": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "'"${HOOKS_DST_DIR}"'/conductor-pre-compact.sh"
          }
        ]
      }
    ]
  }
}'

if [[ -f "${CLAUDE_SETTINGS}" ]] && grep -q "conductor-session-start" "${CLAUDE_SETTINGS}"; then
  if [[ "${FORCE}" == true ]]; then
    echo "检测到已有 conductor hooks 配置，--force 模式下将覆盖。"
  else
    echo "conductor hooks 已注册于 ${CLAUDE_SETTINGS}，跳过。使用 --force 覆盖。"
    echo ""
    echo "安装完成。"
    exit 0
  fi
fi

if command -v jq &>/dev/null; then
  if [[ -f "${CLAUDE_SETTINGS}" ]]; then
    EXISTING=$(cat "${CLAUDE_SETTINGS}")
    echo "${EXISTING}" | jq --argjson new_hooks "$(echo "${HOOKS_JSON}" | jq '.hooks')" \
      '.hooks = (.hooks // {}) * $new_hooks' > "${CLAUDE_SETTINGS}.tmp"
    mv "${CLAUDE_SETTINGS}.tmp" "${CLAUDE_SETTINGS}"
    echo "已合并 conductor hooks 到 ${CLAUDE_SETTINGS}"
  else
    echo "${HOOKS_JSON}" | jq '.' > "${CLAUDE_SETTINGS}"
    echo "已创建 ${CLAUDE_SETTINGS} 并写入 conductor hooks"
  fi
else
  echo ""
  echo "⚠ 未找到 jq，无法自动注册 hooks 到 ${CLAUDE_SETTINGS}。"
  echo "请手动将以下配置合并到 ${CLAUDE_SETTINGS} 的 hooks 字段中："
  echo ""
  echo "${HOOKS_JSON}"
  echo ""
fi

echo ""
echo "安装完成。"
