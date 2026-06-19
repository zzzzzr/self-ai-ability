# example-skill

| 字段 | 值 |
|------|-----|
| type | skill |
| version | 1.0.0 |

示例 skill，可作为新建 capability 的目录与文件结构模板。

## 安装

```bash
# Cursor
./install.sh example-skill
./install.sh example-skill --dest /path/to/project --force

# Claude Code
/plugin install example-skill@self-ai-ability
```

## 行为

用户输入 `/example-skill` 时触发，向用户说明这是一个示例 skill。

## 目录结构

```text
example-skill/
├── .claude-plugin/plugin.json
├── .cursor-plugin/plugin.json
└── skills/example-skill/SKILL.md
```
