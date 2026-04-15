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
| `workflow-conductor` | rule | 通用工作流指挥协议。引导 agent 在多步骤任务中创建和维护核心目标文件（项目根目录 `.ai-objectives/` 下，按时间和业务场景命名），确保任务不遗漏、不偏离、多任务不冲突。安装时会自动将 `.ai-objectives/` 追加到项目 `.gitignore` |

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

对于包含 `references` 的 capability（如 `workflow-conductor`），安装脚本会将 rules 和 references 一并安装到 `.cursor/` 下。rules 中的 probe 通过 `.cursor/references/` 路径按需读取完整协议。

`--dest` 规则：

- `--dest ~` 写入 `~/.cursor/`
- `--dest /path/to/project` 写入 `/path/to/project/.cursor/`
- 不传 `--dest` 时，默认写入 `~/.cursor/`

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
    └── install-cursor-capability.py
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

Cursor 安装脚本处理上面七类资源。其中 `commands` 会被复制到 `~/.cursor/commands/`，作为 Cursor 斜杠命令使用；`references` 会被复制到 `.cursor/references/`，供 rules 按需读取。

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
