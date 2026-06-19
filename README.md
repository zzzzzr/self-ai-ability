# self-ai-ability

个人 AI Agent 能力管理仓库，兼容 Claude Code plugin marketplace 与 Cursor 本地安装。

按「单一 capability」粒度管理 skill、rule、mcp、script 等能力。

## 核心原则

- 每个可安装/可维护单元就是一个 capability，位于 `capabilities/<name>/`
- 每个 capability 只承载一种主 type（skill / rule / mcp / script）
- 默认安装到 `~/.cursor/`，也支持 `--dest` 安装到指定项目
- 不做分类安装，不做全量安装

## 文档导航

| 类别 | 文档 |
|------|------|
| 能力索引 | [capabilities/README.md](capabilities/README.md) |
| 文档索引 | [docs/README.md](docs/README.md) |
| 新增 capability | [docs/contributing.md](docs/contributing.md) |

各 capability 详细说明见对应目录下的 `README.md`。

## 仓库元层

与 README 同级，用于描述和管理能力，本身不是 capability：

| 文件 | 作用 |
|------|------|
| `install.sh` | Cursor 安装入口 |
| `install-cursor-capability.py` | 读取 marketplace，安装 skill/rule/mcp |
| `.cursor-plugin/marketplace.json` | 能力清单 |
| `.claude-plugin/marketplace.json` | Claude Code 能力清单 |

### 安装 capability（Cursor）

```bash
./install.sh --list
./install.sh <capability-name>
./install.sh <capability-name> --dest /path/to/project --force
```

- `type: script` 的能力不可安装，请在仓库内直接运行其 `scripts/`
- `--dest ~` 写入 `~/.cursor/`；`--dest /path/to/project` 写入项目 `.cursor/`

### 安装 capability（Claude Code）

```bash
/plugin marketplace add <your-repo-url>
/plugin install <capability-name>@self-ai-ability
```

## 仓库结构

```text
.
├── README.md
├── install.sh
├── install-cursor-capability.py
├── .cursor-plugin/marketplace.json
├── capabilities/                  # 5 个能力（skill / rule / script）
│   ├── example-skill/
│   ├── workflow-conductor/
│   ├── codex-skill-migrator/
│   ├── multi-project-sync/
│   └── sync-repos/
└── docs/
    ├── contributing.md
    └── install/
```

## 支持的资源类型

skill、rule、mcp 通过 `install.sh` 安装；script 在仓库内运行。

Cursor 安装时：`commands` → `.cursor/commands/`；`rules` → `.cursor/rules/*.mdc`；`references` → `.cursor/references/`。

`plugin.json` 是本仓库自定义清单格式，供 `install.sh` 与 Claude Code `/plugin` 识别，非官方插件规范。
