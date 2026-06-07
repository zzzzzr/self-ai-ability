# 新增 Capability 指南

## 类型（type）

每个 capability 在 `plugin.json` 与 `marketplace.json` 中声明一个 `type`，描述**主交付物**：

| type | 含义 | 安装行为 |
|------|------|----------|
| `skill` | Agent Skill | `install.sh <name>` 安装到 `~/.cursor/skills/` 或项目 |
| `rule` | 规则（可附带 hooks、references） | 安装到 `.cursor/rules/` 等 |
| `mcp` | MCP 服务配置 | 合并到 MCP 配置 |
| `script` | 仓库维护脚本 | **不安装**；在 `capabilities/<name>/scripts/` 内直接运行 |

复合资源（如 rule + hooks）仍只标主 type。`hook`、`command` 等作为附属资源，不单独列为 type。

## 步骤

1. 在 `capabilities/` 下创建目录
2. 补充 `.claude-plugin/plugin.json` 和 `.cursor-plugin/plugin.json`（含 `type`）
3. 放入资源文件（`skills/`、`rules/`、`scripts/` 等）
4. 编写 `capabilities/<name>/README.md`
5. 在根目录两个 `marketplace.json` 中登记
6. 更新 `capabilities/README.md` 索引

## 目录约定

```text
capabilities/<name>/
├── .claude-plugin/plugin.json
├── .cursor-plugin/plugin.json
├── README.md
├── skills/<skill-name>/SKILL.md      # type: skill
├── rules/<rule-name>.md              # type: rule
├── mcp-cursor.json                   # type: mcp
├── scripts/ + config/                # type: script
└── ...
```

## script 类 capability

- 不通过 `install.sh` 安装；`install.sh` 会拒绝并提示脚本路径
- 个人配置文件放在 `config/` 下，example 提交、实际 config 写入 `.gitignore`
- 在 README 中说明首次配置与常用命令

## 人工安装后步骤

需要密钥、首次登录等人工操作，写到 `docs/install/<capability-name>.md`。

## 仓库元层（不是 capability）

以下文件与 README 同级，**不**放入 `capabilities/`，**不**登记 marketplace：

- `install.sh` / `install-cursor-capability.py` — 安装入口
- `.cursor-plugin/marketplace.json` — 能力清单
