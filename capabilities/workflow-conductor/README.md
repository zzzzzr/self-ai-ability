# workflow-conductor

| 字段 | 值 |
|------|-----|
| type | rule |
| version | 1.1.0 |

通用工作流指挥协议。引导 agent 在多步骤任务中创建和维护核心目标文件（`.ai-objectives/`），确保任务不遗漏、不偏离。

含 hooks 执行保障层（SessionStart 发现注入 / PreCompact 约束保全）。安装到项目时会自动将 `.ai-objectives/` 追加到 `.gitignore`。

## 安装

```bash
# Cursor（推荐安装到项目）
./install.sh workflow-conductor --dest /path/to/project --force

# Claude Code
/plugin install workflow-conductor@self-ai-ability
```

## 资源

- `rules/session-objective.md` — 探针规则（alwaysApply）
- `references/conductor-protocol.md` — 完整协议（按需读取）
- `hooks/` — SessionStart、PreCompact 保障脚本

## 目录结构

```text
workflow-conductor/
├── rules/
├── references/
└── hooks/
```
