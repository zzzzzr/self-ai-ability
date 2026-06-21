#!/usr/bin/env bash
# ai-hub-sync-session-start.sh — sessionStart hook
# 检查 AI Hub 同步配置，向 AI 注入上下文，驱动其在会话开始时执行同步检查。
set -euo pipefail

INPUT=$(cat)

PROJECT_DIR="${CURSOR_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}"

context=$(python3 - "$PROJECT_DIR" <<'PY'
import sys, json, os
from datetime import date
from pathlib import Path

project = Path(sys.argv[1])
today = date.today().isoformat()

def load_config(path: Path) -> dict:
    if path.is_file():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}

# 读取全局配置和项目配置
global_cfg = load_config(Path.home() / ".cursor/ai-hub-sync.json")
project_cfg = load_config(project / ".cursor/ai-hub-sync.json")

global_repos = global_cfg.get("repos", {})
project_repos = project_cfg.get("repos", {})

# 无任何配置
if not global_repos:
    print("【最高优先级 · 阻塞】检测到尚未配置 AI Hub 同步。")
    print("你必须在本轮回复的最开头执行以下初始化引导，不得跳过，不得先回答用户的原始问题：")
    print("1. 告知用户即将引导完成 AI Hub 同步初始化")
    print("2. 询问用户 AI Hub 仓库的本地路径，校验目录存在后自动检测安装脚本（先找 install.sh，再找 scripts/install.sh）")
    print("3. 执行 <repoPath>/<installScript> --list 列出可用插件，供用户选择")
    print("4. 将配置写入 ~/.cursor/ai-hub-sync.json")
    print("5. 询问是否立即执行一次同步")
    print("在用户完成初始化或明确选择跳过之前，不得直接回答用户的原始问题。")
    sys.exit(0)

# 合并：项目 plugins 覆盖全局同名 repo 的 plugins，其他字段继承全局
merged = {}
for name, repo in global_repos.items():
    merged[name] = dict(repo)
    if name in project_repos and "plugins" in project_repos[name]:
        merged[name]["plugins"] = project_repos[name]["plugins"]

# 找出今天未同步的 repo
pending = []
for name, repo in merged.items():
    last = repo.get("lastSyncDate")
    if last != today:
        pending.append({
            "name": name,
            "repoPath": repo.get("repoPath", "（未配置路径）"),
            "plugins": repo.get("plugins", []),
            "lastSyncDate": last or "从未",
        })

if not pending:
    sys.exit(0)

lines = ["检测到以下 AI Hub 仓库今天尚未同步插件：", ""]
for i, r in enumerate(pending, 1):
    plugins_str = ", ".join(r["plugins"]) if r["plugins"] else "（未配置插件）"
    lines.append(f"  [{i}] {r['name']}")
    lines.append(f"      路径: {r['repoPath']}")
    lines.append(f"      插件: {plugins_str}")
    lines.append(f"      上次同步: {r['lastSyncDate']}")
lines.append("")
lines.append("在回复用户问题之前，必须先向用户展示上述列表并询问：")
lines.append("「检测到以上仓库今天尚未同步，是否现在更新？（输入序号、all 或 skip）」")
lines.append("用户选择后立即执行同步：cd <repoPath> && git pull，再对每个插件调用 <installScript> <plugin> --dest <当前项目目录> --force。")
lines.append("同步完成后将该 repo 的 lastSyncDate 更新为今天，写回 ~/.cursor/ai-hub-sync.json。")
print("\n".join(lines))
PY
)

if [[ -z "${context:-}" ]]; then
    exit 0
fi

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
