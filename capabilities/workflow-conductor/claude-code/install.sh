#!/usr/bin/env bash
# install.sh — 将 Session Objective Protocol 安装到 ~/.claude/CLAUDE.md
# 幂等：重复执行不会重复写入；--force 强制替换已有内容

set -euo pipefail

FORCE=false
if [[ "${1:-}" == "--force" ]]; then
  FORCE=true
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE_FILE="${SCRIPT_DIR}/session-objective-protocol.md"
CLAUDE_DIR="${HOME}/.claude"
CLAUDE_MD="${CLAUDE_DIR}/CLAUDE.md"

MARKER="## Session Objective Protocol"

# 检查模板文件存在
if [[ ! -f "${TEMPLATE_FILE}" ]]; then
  echo "ERROR: 模板文件不存在: ${TEMPLATE_FILE}" >&2
  exit 1
fi

# 确保 ~/.claude 目录存在
mkdir -p "${CLAUDE_DIR}"

# 幂等检查：如果已包含 marker
if [[ -f "${CLAUDE_MD}" ]] && grep -qF "${MARKER}" "${CLAUDE_MD}"; then
  if [[ "${FORCE}" == false ]]; then
    echo "Session Objective Protocol 已存在于 ${CLAUDE_MD}，跳过写入。"
    echo "如需更新，请使用 --force 参数强制替换。"
    exit 0
  fi
  # --force: 删除旧的 Session Objective Protocol 段落（从 marker 到下一个同级 ## 标题或文件末尾）
  # 需要感知 ``` 代码围栏，避免把代码块内的 ## 当作段落边界
  awk -v marker="${MARKER}" '
    BEGIN { skip=0; in_fence=0 }
    /^```/ { in_fence = !in_fence }
    !in_fence && $0 == marker { skip=1; next }
    skip && !in_fence && /^## / { skip=0 }
    !skip { print }
  ' "${CLAUDE_MD}" > "${CLAUDE_MD}.tmp"
  mv "${CLAUDE_MD}.tmp" "${CLAUDE_MD}"
  echo "已移除旧的 Session Objective Protocol 段落。"
fi

CONTENT="$(cat "${TEMPLATE_FILE}")"

# 如果 CLAUDE.md 存在，追加；否则创建
if [[ -f "${CLAUDE_MD}" ]]; then
  # 追加前加空行分隔
  printf '\n%s\n' "${CONTENT}" >> "${CLAUDE_MD}"
  echo "已追加 Session Objective Protocol 到 ${CLAUDE_MD}"
else
  # 创建新文件，加上顶级标题
  {
    echo "# Global Instructions"
    echo ""
    echo "${CONTENT}"
  } > "${CLAUDE_MD}"
  echo "已创建 ${CLAUDE_MD} 并写入 Session Objective Protocol"
fi

# 尝试将 .ai-objectives/ 追加到当前项目的 .gitignore
# 如果通过 --project 指定了项目目录，则使用该目录；否则使用当前工作目录
PROJECT_DIR="${2:-.}"
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
