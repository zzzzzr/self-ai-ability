# cursor-sync

| 字段 | 值 |
|------|-----|
| type | rule |
| version | 1.0.0 |

为 Cursor 提供多仓库 AI 插件自动同步能力。每次会话开始时自动检测并按需更新已配置仓库的插件，解决 Cursor 没有原生 Marketplace 自动更新机制的问题。

## 背景

Claude Code 通过 `.claude/settings.json` 的 `extraKnownMarketplaces` 原生支持注册 git 源并自动同步，而 Cursor 没有等效机制。本 capability 通过 `alwaysApply: true` 的 Rule + `/cursor-sync` Skill 弥补这一缺口。

## 安装

```bash
# Cursor（全局）
./install.sh cursor-sync --global

# Cursor（项目级）
./install.sh cursor-sync
```

## 使用

安装后：

1. 首次开启 Cursor 会话 → Rule 自动触发 → 提示运行 `/cursor-sync` 完成初始化
2. 运行 `/cursor-sync` → Skill 引导配置仓库路径、安装脚本路径和插件列表
3. 后续每次会话 → Rule 自动检查，当天未同步的仓库会列出供选择

## 配置文件

| 文件 | 作用 |
|------|------|
| `~/.cursor/ai-hub-sync.json` | 全局配置（仓库路径、安装脚本、插件列表、同步历史） |
| `.cursor/ai-hub-sync.json` | 项目配置（`plugins` 字段整体覆盖全局同名仓库） |

配置格式示例：

```json
{
  "repos": {
    "my-ai-hub": {
      "repoPath": "/Users/xxx/my-ai-hub",
      "installScript": "scripts/install.sh",
      "plugins": ["plugin-a", "plugin-b"],
      "lastSyncDate": "2026-06-19",
      "syncHistory": [
        { "date": "2026-06-19", "plugins": ["plugin-a", "plugin-b"], "result": "success" }
      ]
    }
  }
}
```

## 目录结构

```text
cursor-sync/
├── rules/ai-hub-sync.mdc         # alwaysApply: true，会话同步检查
└── skills/cursor-sync/
    └── SKILL.md                  # /cursor-sync 配置引导 Skill
```
