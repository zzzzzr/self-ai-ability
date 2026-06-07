# self-ai-ability

个人 AI Agent 能力管理仓库，兼容 `Claude Code` plugin marketplace 协议和 `Cursor` 本地安装脚本。

按"单一 capability"粒度管理和安装 `skill`、`agent`、`hook`、`mcp`、`command` 等能力。

## 核心原则

- 每个可安装单元就是一个 capability
- 每个 capability 只承载一种主能力
- Cursor 端支持按 capability 名称安装
- 默认安装到 `~/.cursor/`，也支持安装到指定项目
- 不做分类安装，不做全量安装

## 当前内置能力

| capability | 类型 | 说明 |
|---|---|---|
| `example-skill` | skill | 示例 skill，可作为新建 capability 的模板 |
| `workflow-conductor` | rule + hooks | 通用工作流指挥协议。引导 agent 在多步骤任务中创建和维护核心目标文件（项目根目录 `.ai-objectives/` 下，按时间和业务场景命名），确保任务不遗漏、不偏离、多任务不冲突。含 hooks 执行保障层（SessionStart 发现注入 / Stop 步骤提醒 / PreCompact 约束保全），安装时会自动将 `.ai-objectives/` 追加到项目 `.gitignore` |
| `codex-skill-migrator` | skill | 将外部 AI 仓库（plugins/ 或 capabilities/ 结构）中的 Skill 和 MCP 配置迁移到 Codex，支持 dry-run 与 MCP 合并到 ~/.codex/config.toml |

## 快速开始

### Claude Code

```bash
# 1. 添加 marketplace
/plugin marketplace add <your-repo-url>

# 2. 安装指定 capability
/plugin install example-skill@self-ai-ability
```

### Cursor

```bash
# 1. 查看可安装 capability
/path/to/self-ai-ability/scripts/install.sh --list

# 2. 安装指定 capability（默认安装到 ~/.cursor/）
/path/to/self-ai-ability/scripts/install.sh <capability-name>

# 3. 安装到具体项目（rules 和 references 会安装到 <project>/.cursor/ 下）
/path/to/self-ai-ability/scripts/install.sh <capability-name> --dest /path/to/project

# 4. 冲突时强制覆盖
/path/to/self-ai-ability/scripts/install.sh <capability-name> --force
```

对于包含 `references` 的 capability，安装脚本会将 rules 和 references 一并安装到 `.cursor/` 下。Cursor 项目规则会以 `.mdc` 文件落盘到 `.cursor/rules/`。

`--dest` 规则：

- `--dest ~` 写入 `~/.cursor/`
- `--dest /path/to/project` 写入 `/path/to/project/.cursor/`
- 不传 `--dest` 时，默认写入 `~/.cursor/`

## 批量同步工具

当你有多个项目（或同一项目的多个副本）需要安装相同的 capability 时，可以用 `scripts/sync-capabilities.sh` 一条命令同步到所有目标。

```bash
# 1. 复制配置模板并填入你的目标项目路径
cp scripts/sync-config.example.json scripts/sync-config.json

# 2. 执行任意安装命令，{dest} 会被逐个替换为配置中的目标路径
scripts/sync-capabilities.sh "python3 scripts/install-cursor-capability.py workflow-conductor --dest {dest} --force"

# 也可以执行其他仓库的安装脚本
scripts/sync-capabilities.sh "bash ~/other-repo/install.sh --project={dest}"
```

配置文件 `sync-config.json`（不提交到仓库，已 gitignore）：

```json
{
  "targets": [
    "~/Documents/for_git/project-a",
    "~/Documents/for_hub/project-a",
    "~/Documents/for_git/project-b"
  ]
}
```

### 同步 plugins 配置

当你需要让多个项目的 `.cursor/settings.json` 和 `.claude/settings.json` 中的 plugins 保持一致时，使用 `scripts/sync-plugins.py`。

```bash
# 以标准配置为准，替换所有目标项目的 plugins（删除多余的）
python3 scripts/sync-plugins.py --from-file scripts/plugins-standard.json --replace

# 先 dry-run 查看变更预览
python3 scripts/sync-plugins.py --from-file scripts/plugins-standard.json --replace --dry-run

# 以某个项目为 source，同步到其他目标
python3 scripts/sync-plugins.py --from-project ~/Documents/for_git/overseas-payment

# 只追加新 plugins，不删除已有的
python3 scripts/sync-plugins.py --from-file plugins-to-add.json

# 只同步到 Cursor 或 Claude Code
python3 scripts/sync-plugins.py --from-file scripts/plugins-standard.json --replace --platform cursor
python3 scripts/sync-plugins.py --from-file scripts/plugins-standard.json --replace --platform claude
```

选项说明：

| 选项 | 作用 |
|------|------|
| `--from-file FILE` | 从 JSON 文件读取 plugins |
| `--from-project DIR` | 从某个项目的 settings.json 读取 plugins |
| `--replace` | 替换模式：以 source 为准，删除目标中多余的 plugins |
| `--force` | 覆盖同名 plugin（不删除多余的） |
| `--platform cursor/claude/both` | 指定同步到哪个平台（默认 both） |
| `--dry-run` | 预览变更，不实际写入 |
| `--exclude DIR` | 排除某个目标项目 |
| `--config FILE` | 指定 targets 配置文件（默认 sync-config.json） |

标准配置文件 `scripts/plugins-standard.json` 提交到仓库，作为所有项目的 plugins 基准。新增或移除 plugin 时更新此文件后执行 `--replace` 即可。

### 批量 Git 更新

当你在一个父目录下维护多个 Git 子仓库（如 `~/Documents/for_git`）时，可以用 `scripts/sync-repos.sh` 批量执行 `git fetch origin` + pull。

```bash
# 1. 复制配置模板并填入父目录与排除项
cp scripts/sync-repos-config.example.json scripts/sync-repos-config.json

# 2. 使用 config 中的 target 批量更新
scripts/sync-repos.sh

# 3. 临时指定 target 并追加排除
scripts/sync-repos.sh --target ~/Documents/for_hub --exclude foo,bar

# 4. 预览将执行的 git 命令
scripts/sync-repos.sh --target ~/Documents/for_git --dry-run

# 5. 单次覆盖 pull 策略（默认 rebase）
scripts/sync-repos.sh --pull-mode ff-only
```

配置文件 `sync-repos-config.json`（不提交到仓库，已 gitignore）：

```json
{
  "target": "~/Documents/for_git",
  "pull_mode": "rebase",
  "exclude": ["archived-demo", "tmp-playground"]
}
```

行为说明：

- 只扫描 `target` 的**直接子文件夹**（一层，不递归）
- 非 Git 目录、排除项、隐藏目录（`.` 开头）计入 `skipped`
- `pull_mode` 支持 `rebase`（默认）、`ff-only`、`merge`；CLI `--pull-mode` 优先于 config
- pull 失败时若处于 rebase 状态会自动 `git rebase --abort`，不自动解决冲突
- 全部处理完后输出「遇到问题的子目录」清单；有失败时退出码非 0

| 选项 | 作用 |
|------|------|
| `--target PATH` | 覆盖 config 中的父目录 |
| `--pull-mode MODE` | 覆盖 pull 策略：`rebase` / `ff-only` / `merge` |
| `--exclude NAME` | 临时追加排除的子文件夹名（与 config exclude 取并集） |
| `--config FILE` | 指定配置文件（默认 `scripts/sync-repos-config.json`） |
| `--dry-run` | 只打印计划执行的 git 命令 |

## 仓库结构

```text
.
├── .claude-plugin/marketplace.json
├── .cursor-plugin/marketplace.json
├── capabilities/
│   └── <your-capability>/
├── docs/
│   └── install/
│       └── <capability-name>.md
└── scripts/
    ├── install.sh
    ├── install-cursor-capability.py
    ├── sync-capabilities.sh
    ├── sync-repos.sh
    ├── sync-repos.py
    ├── sync-plugins.py
    ├── plugins-standard.json
    ├── sync-config.example.json
    └── sync-repos-config.example.json
```

每个 capability 都是一个独立 plugin，内部只放自己需要的资源和两份薄清单：

```text
capabilities/<name>/
├── .claude-plugin/plugin.json
├── .cursor-plugin/plugin.json
└── <ability files>
```

## 支持的资源类型

- `skills`
- `agents`
- `hooks`
- `mcpServers`
- `commands`
- `rules`
- `references`

Cursor 安装脚本处理上面七类资源。其中 `commands` 会被复制到 `.cursor/commands/`，作为 Cursor 斜杠命令使用；`rules` 会安装为 `.cursor/rules/*.mdc`；`references` 会被复制到 `.cursor/references/`，供 rules 按需读取。

## plugin.json 说明

每个 capability 内的 `.claude-plugin/plugin.json` 和 `.cursor-plugin/plugin.json` 是本仓库自定义的清单格式，用于声明该 capability 包含哪些资源。它们**不是** Claude Code 或 Cursor 官方的插件规范，仅供本仓库的安装脚本（`scripts/install.sh`、`scripts/install-cursor-capability.py`）和 Claude Code `/plugin` 命令识别使用。

## 新增一个 capability

1. 在 `capabilities/` 下创建目录
2. 补充 `.claude-plugin/plugin.json`
3. 补充 `.cursor-plugin/plugin.json`
4. 放入真实资源文件
5. 在根目录两个 `marketplace.json` 中登记 capability

推荐约定：

- `skill` 使用 `skills/<skill-name>/SKILL.md`
- `agent` 使用 `agents/<agent-name>.md`
- `hook` 使用 `hooks/hooks.json` 加配套脚本
- `mcp` 使用 `mcp-claude.json` 和 `mcp-cursor.json`
- `command` 使用 `commands/<commandName>.md`
- `rule` 使用 `rules/<rule-name>.md`（`alwaysApply: true` 的轻量规则）
- `reference` 使用 `references/<name>.md`（供 rules 按需 Read 的详细文档）

最小 skill 结构示例：

```text
capabilities/<capability-name>/
├── .claude-plugin/plugin.json
├── .cursor-plugin/plugin.json
└── skills/<skill-name>/SKILL.md
```

## 人工操作说明

需要人工完成的安装后步骤，统一放在 `docs/install/` 下，例如：

- `docs/install/<capability-name>.md`

这里适合写密钥配置、首次登录、依赖安装等人工步骤。
