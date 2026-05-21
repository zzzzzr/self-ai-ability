---
name: codex-skill-migrator
description: "将外部 AI 仓库中的 Skill 和 MCP 配置迁移到 Codex。适用于 plugins/<name>/skills/<skill>/SKILL.md 或 capabilities/<name>/skills/<skill>/SKILL.md 结构的仓库；支持 dry-run、按 plugin 或 capability 选择、生成 MCP TOML 片段并合并到 ~/.codex/config.toml。当用户提到迁移 Skill 到 Codex、迁移 MCP 到 Codex、把 Cursor/Claude Code 的插件仓库接入 Codex、从外部仓库安装 Skill 到 ~/.agents/skills 时必须使用此技能。"
---

# Codex Skill Migrator

这是仓库级 Skill/MCP 迁移的主入口。

优先复用 bundled scripts，不要手工重写迁移逻辑。

**脚本位置**：所有脚本位于本 skill 安装目录的 `scripts/` 子目录下。  
运行前先定位 skill 目录（Codex 环境下为 `~/.agents/skills/codex-skill-migrator/scripts/`），使用绝对路径调用。

## 适用范围

- 源仓库采用 `plugins/<name>/skills/<skill>/SKILL.md` 结构
- 或采用 `capabilities/<name>/skills/<skill>/SKILL.md` 结构
- 仓库中可选存在 `mcp.json`、`mcp-cursor.json`、`mcp-claude.json`

如果仓库不是这两类结构，先阅读 [references/supported-layouts.md](references/supported-layouts.md)，再决定是否需要扩脚本。

## 默认工作方式

1. 先识别源仓库根目录，并显式传 `--repo-root`
2. 默认先执行 `--dry-run`
3. 只迁 Skill 时使用 `--skills-only`
4. 只迁 MCP 时使用 `--mcp-only`
5. 只有在用户明确允许修改本机 Codex 配置时，才追加 `--apply-mcp`

## 常用命令

> 以下示例中 `$SKILL_DIR` 代表本 skill 的安装路径。  
> Codex 环境下为 `~/.agents/skills/codex-skill-migrator`。  
> 执行前请将 `$SKILL_DIR` 替换为实际绝对路径。

查看可迁移的 plugin 或 capability：

```bash
bash $SKILL_DIR/scripts/migrate-to-codex.sh --repo-root /path/to/repo --list
```

先跑一次 dry-run：

```bash
bash $SKILL_DIR/scripts/migrate-to-codex.sh --repo-root /path/to/repo --all --dry-run
```

迁移 `capabilities/` 结构仓库：

```bash
bash $SKILL_DIR/scripts/migrate-to-codex.sh \
  --repo-root /path/to/repo \
  --source-layout capabilities \
  --all \
  --skills-only \
  --dry-run
```

正式迁 Skill：

```bash
bash $SKILL_DIR/scripts/migrate-to-codex.sh \
  --repo-root /path/to/repo \
  --all \
  --skills-only
```

生成并合并 MCP：

```bash
bash $SKILL_DIR/scripts/migrate-to-codex.sh \
  --repo-root /path/to/repo \
  --mcp-only \
  --apply-mcp
```

## Bundled Scripts

- `$SKILL_DIR/scripts/migrate_to_codex.py`：主迁移脚本（Python 3，无额外依赖）
- `$SKILL_DIR/scripts/migrate-to-codex.sh`：shell 包装入口（调用上面的 Python 脚本）

如果用户只想迁单个 plugin 或 capability，使用 `--plugin <name>`，可重复传入。
