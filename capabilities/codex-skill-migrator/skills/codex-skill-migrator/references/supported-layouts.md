# Supported Layouts

当前脚本支持两类源结构。

## plugins 布局

```text
repo/
└── plugins/
    └── <plugin-name>/
        ├── skills/
        │   └── <skill-name>/
        │       └── SKILL.md
        └── mcp.json | mcp-cursor.json | mcp-claude.json
```

适用示例：

- 任何以 `plugins/` 为顶层目录组织插件的仓库

## capabilities 布局

```text
repo/
└── capabilities/
    └── <capability-name>/
        ├── skills/
        │   └── <skill-name>/
        │       └── SKILL.md
        └── mcp.json | mcp-cursor.json | mcp-claude.json
```

适用示例：

- 任何以 `capabilities/` 为顶层目录组织能力单元的仓库

## 输出位置

- Skill 默认安装到 `~/.agents/skills`
- MCP 默认生成 TOML 片段，并可合并到 `~/.codex/config.toml`

## 建议

- 先执行 `--dry-run`
- 如果仓库同时存在 `plugins/` 和 `capabilities/`，显式传 `--source-layout`
- 如果仓库里没有 `mcp*.json`，`MCP` 输出为空属于正常情况
