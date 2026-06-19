# Capabilities

本目录包含仓库登记的全部能力（共 6 个）。按 `type` 分组：

## skill

| 名称 | 说明 | 文档 |
|------|------|------|
| `example-skill` | 示例 skill，可作为新建 capability 的模板 | [README](example-skill/README.md) |
| `codex-skill-migrator` | 将外部 AI 仓库 Skill/MCP 迁移到 Codex | [README](codex-skill-migrator/README.md) |

## rule

| 名称 | 说明 | 文档 |
|------|------|------|
| `workflow-conductor` | 多步骤任务核心目标协议 + hooks 保障层 | [README](workflow-conductor/README.md) |
| `cursor-sync` | Cursor 多仓库 AI 插件自动同步（含 `/cursor-sync` 配置 Skill） | [README](cursor-sync/README.md) |

## script

仓库内直接运行，不通过 `install.sh` 安装。

| 名称 | 说明 | 文档 |
|------|------|------|
| `multi-project-sync` | 多项目批量命令执行 + plugins 对齐 | [README](multi-project-sync/README.md) |
| `sync-repos` | 父目录下子 Git 仓库批量 fetch + pull | [README](sync-repos/README.md) |

## 新增 capability

见 [docs/contributing.md](../docs/contributing.md)。
