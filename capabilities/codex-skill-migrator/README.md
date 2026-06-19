# codex-skill-migrator

| 字段 | 值 |
|------|-----|
| type | skill |
| version | 1.0.0 |

将外部 AI 仓库（`plugins/` 或 `capabilities/` 结构）中的 Skill 和 MCP 配置迁移到 Codex。支持 dry-run、按 capability 选择、MCP 合并到 `~/.codex/config.toml`。

## 安装

```bash
./install.sh codex-skill-migrator

# Claude Code
/plugin install codex-skill-migrator@self-ai-ability
```

## 使用

安装后通过 skill 触发，脚本位于 `skills/codex-skill-migrator/scripts/`：

```bash
bash $SKILL_DIR/scripts/migrate-to-codex.sh --repo-root /path/to/repo --list
bash $SKILL_DIR/scripts/migrate-to-codex.sh --repo-root /path/to/repo --all --dry-run
```

## 目录结构

```text
codex-skill-migrator/
└── skills/codex-skill-migrator/
    ├── SKILL.md
    ├── scripts/
    └── references/
```
