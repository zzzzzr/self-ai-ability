---
name: cursor-sync
description: "配置或修改 AI Hub 插件自动同步。触发场景：'/cursor-sync'、'配置插件同步'、'初始化同步配置'、'修改同步配置'、'更新同步插件列表'、'ai-hub 同步'。"
---

# cursor-sync — AI Hub 插件同步配置

> **为什么没有 Claude Code 版本？**
> Claude Code 通过 `.claude/settings.json` 的 `extraKnownMarketplaces` 字段原生支持注册 git 源并自动同步，无需额外工具。本 Skill 专为 Cursor 设计，因为 Cursor 没有等效的原生 Marketplace 自动更新机制。

## 触发方式

用户输入 `/cursor-sync` 时执行本 Skill。

---

## 执行流程

### 第一步：感知当前状态

读取以下配置文件：
- 全局：`~/.cursor/ai-hub-sync.json`
- 项目：`.cursor/ai-hub-sync.json`

按合并规则得出当前生效配置（项目 `plugins` 字段整体覆盖全局同名 repo 的 `plugins`，其余字段继承全局）。

根据结果进入对应模式：
- **全局配置不存在或 `repos` 为空** → 初始化模式
- **已有配置** → 编辑模式

---

### 【初始化模式】

**① 询问配置 scope**

```
请选择配置写入位置：
  [1] 全局配置 ~/.cursor/ai-hub-sync.json（推荐，所有项目共享仓库路径）
  [2] 项目配置 .cursor/ai-hub-sync.json（仅当前项目生效）
```

**② 询问仓库信息**

```
请输入 AI Hub 仓库的本地路径（例如 /Users/xxx/Documents/my-ai-hub）：
```

收到路径后校验：
- 目录是否存在（`ls <path>`）
- 自动检测安装脚本：按顺序检查 `install.sh` → `scripts/install.sh`，取第一个存在的文件路径

校验失败（目录不存在或两个路径均未找到安装脚本）则提示重新输入，不要继续。

若自动检测到安装脚本，展示给用户确认：
```
检测到安装脚本: install.sh（直接回车确认，或输入其他相对路径覆盖）：
```

如需配置多个仓库，询问：
```
是否还有其他 AI Hub 仓库需要配置？（输入路径或直接回车跳过）
```

**③ 列出可用插件**

对每个仓库，执行 `<repoPath>/<installScript> --list` 获取插件列表，展示给用户：

```
my-ai-hub 可用插件：
  [1] plugin-a
  [2] plugin-b
  [3] plugin-c
  ...

请输入要同步的插件序号（逗号分隔，如 1,3），或输入 all 选择全部：
```

**④ 写入配置文件**

根据选择的 scope 写入配置。全局配置格式：

```json
{
  "repos": {
    "my-ai-hub": {
      "repoPath": "/Users/xxx/my-ai-hub",
      "installScript": "install.sh",
      "plugins": ["plugin-a", "plugin-b"],
      "lastSyncDate": null,
      "syncHistory": []
    }
  }
}
```

写入后告知用户配置文件路径。

**⑤ 询问是否立即同步**

```
配置完成。是否立即执行一次同步？（y/n）
```

选 y 则执行同步（参照 Rule 的 Step 4 逻辑）。

---

### 【编辑模式】

展示当前生效配置，标注每个字段来源（全局/项目）：

```
当前同步配置（合并后生效）：

仓库: my-ai-hub
  repoPath:      /Users/xxx/my-ai-hub             [来源: 全局]
  installScript: install.sh                        [来源: 全局]
  plugins:       plugin-a, plugin-b               [来源: 项目覆盖]
  lastSyncDate:  2026-06-18                        [来源: 全局]
  syncHistory:   3 条记录（最近: 2026-06-18 success）

请选择操作：
  [1] 修改仓库路径
  [2] 修改安装脚本路径
  [3] 修改插件列表
  [4] 新增仓库
  [5] 删除仓库
  [6] 切换配置 scope（全局 ↔ 项目）
  [7] 立即执行一次同步
  [8] 查看同步历史
  [9] 清除配置
  [q] 退出
```

等待用户选择，按选择执行对应操作。

**[3] 修改插件列表** 需重新展示完整插件列表（同初始化模式 Step ③），当前已选插件高亮标注。

**[6] 切换 scope** 说明：
- 全局 → 项目：将当前全局配置中该 repo 的 `plugins` 字段复制到项目配置，后续项目配置覆盖全局
- 项目 → 全局：删除项目配置中该 repo 的 `plugins` 字段，恢复继承全局

**[9] 清除配置** 前确认：
```
确认清除？这将删除配置文件中的所有仓库记录。（输入 yes 确认）
```

---

## 配置文件格式参考

**全局** `~/.cursor/ai-hub-sync.json`：
```json
{
  "repos": {
    "my-ai-hub": {
      "repoPath": "/Users/xxx/my-ai-hub",
      "installScript": "install.sh",
      "plugins": ["plugin-a", "plugin-b"],
      "lastSyncDate": "2026-06-19",
      "syncHistory": [
        { "date": "2026-06-19", "plugins": ["plugin-a", "plugin-b"], "result": "success" },
        { "date": "2026-06-18", "plugins": ["plugin-a"], "result": "success" }
      ]
    }
  }
}
```

**项目** `.cursor/ai-hub-sync.json`（只写差异，`plugins` 覆盖全局）：
```json
{
  "repos": {
    "my-ai-hub": {
      "plugins": ["plugin-c", "plugin-d"]
    }
  }
}
```
