# Conductor Hooks 执行保障层设计文档

> 创建时间: 2026-05-21 14:32
> 状态: 方案设计

## 1. 背景与动机

workflow-conductor 协议目前通过 `rules/session-objective.md`（安装到 Cursor 的 `.cursor/rules/` 或 Claude Code 的 `CLAUDE.md`）引导 agent 管理多步骤任务的目标文件。

实际使用中发现，协议在以下场景下的执行可靠性不够理想：

- **长对话 context 衰减**: 对话越长，agent 对 rule 中指令的注意力越弱，可能遗漏"步骤间检查"等要求
- **Context 压缩后丢失约束**: 自动 compact 后，objective 文件中的具体约束和进度可能不在压缩摘要中
- **会话恢复时遗忘**: 新会话开始时，agent 可能不主动扫描 `.ai-objectives/` 目录
- **进度更新被跳过**: 步骤完成后 agent 可能忘记勾选 checklist

这些问题的根源不是协议设计有缺陷，而是 **rule 和 hook 在"强制性"上处于不同层面**。

## 2. Rule 与 Hook 的本质区别

这两者常被混淆为"都是强制执行的"，但它们的强制性机制完全不同：

### Rule（协议层）

- **执行者**: Agent（LLM 自身）
- **加载方式**: 每次 context 加载时包含在系统指令中
- **强制性**: Agent 层面的强制——agent 知道必须遵守，也会努力遵守。它不会"主动选择"忽略 rule
- **失效场景**:
  - Context window 被压缩后，rule 文本本身还在，但 rule 引用的上下文（如 objective 文件内容）可能已丢失
  - 对话过长时，agent 对 rule 中复杂多步骤指令的注意力会衰减
  - 多步骤任务中间，rule 中的检查要求可能被当前任务的复杂性淹没
- **擅长**: 语义级判断（触发条件评估、步骤拆分决策、约束冲突处理）

### Hook（执行层）

- **执行者**: 运行时系统（IDE/CLI 框架），在 agent 循环之外运行
- **加载方式**: 通过 `hooks.json` / `settings.json` 注册，在生命周期事件触发时自动执行脚本
- **强制性**: 系统层面的强制——不经过 agent 大脑，由运行时框架在确定的时间点触发确定的脚本。Agent 无法跳过、无法选择不执行
- **失效场景**: 仅当脚本本身出错（crash/timeout）时才会失效
- **擅长**: 确定性操作（文件检测、内容注入、阻止/放行决策）
- **不擅长**: 语义级推理（无法判断"这个步骤是否应该拆分"）

### 结论

Rule 和 Hook 不是替代关系，而是互补关系：

```
┌─────────────────────────────────────────────────┐
│  Hook（执行层）                                   │
│  确定性保障：在关键节点主动把信息送到 agent 面前      │
│  ┌─────────────────────────────────────────────┐ │
│  │  Rule（协议层）                               │ │
│  │  语义级指导：告诉 agent 如何判断、决策、行动     │ │
│  └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

Conductor 的 rule 协议负责"教 agent 怎么做"，hook 负责"确保 agent 在关键时刻拿到做判断所需的信息"。

## 3. 方案设计

### 3.1 三个 Hook

#### Hook 1: SessionStart — 发现注入

- **触发时机**: 每次会话/对话开始
- **逻辑**: 扫描项目 `.ai-objectives/*.md`，找到 `status: active` 的文件，读取 frontmatter 中的 `objective` 和 `created` 字段，拼成摘要文本注入 agent context
- **输出**:
  - Claude Code: 通过 `hookSpecificOutput.additionalContext` 注入
  - Cursor: 通过 `additional_context` 注入
- **无 active 文件时**: 静默退出（exit 0，无输出），不注入任何内容

#### Hook 2: Stop — 步骤间检查保障（仅 Claude Code）

- **触发时机**: agent 每次完成回复后
- **逻辑**: 如果存在 active objective 文件，读取文件内容，生成提醒（当前进度、未完成步骤数）
- **输出**: 通过 `hookSpecificOutput.additionalContext` 静默注入 context，让 agent 自行决定是否需要更新 objective
- **防死循环**: 检查 `stop_hook_active` 字段，如果为 `true` 则跳过（避免 hook 触发的 stop 又触发 hook）
- **仅 Claude Code**: Cursor 的 `stop` hook 只支持 `followup_message`（会自动提交新消息导致不受控循环），不支持静默 context 注入，因此 Cursor 端不启用此 hook

#### Hook 3: PreCompact — 约束保全

- **触发时机**: context 压缩前
- **逻辑**: 读取当前 active objective 文件的完整内容（核心目标、执行进度、关键约束），注入到 context 中
- **输出**:
  - Claude Code: 通过 `hookSpecificOutput.additionalContext` 注入，确保压缩摘要中保留关键约束
  - Cursor: 通过 `user_message` 展示提醒（Cursor 的 preCompact 是观察性 hook）
- **目的**: 即使 compact 过程压缩了之前的对话，objective 文件的核心内容会作为"新注入的 context"被保留

### 3.2 平台差异对照

| 维度 | Claude Code | Cursor |
|---|---|---|
| 配置位置 | `~/.claude/settings.json` 或 `.claude/settings.json` 的 `hooks` 字段 | `.cursor/hooks.json` |
| 事件命名 | PascalCase: `SessionStart`, `Stop`, `PreCompact` | camelCase: `sessionStart`, `stop`, `preCompact` |
| SessionStart context 注入 | `hookSpecificOutput.additionalContext` | `additional_context` |
| Stop hook | 支持 `additionalContext`（静默注入） | 仅支持 `followup_message`（会触发新一轮对话），不启用 |
| PreCompact | 支持 `additionalContext` + 可 block | 观察性 hook，支持 `user_message` |
| 启用的 hook 数 | 3 个（SessionStart + Stop + PreCompact） | 2 个（sessionStart + preCompact） |

### 3.3 文件结构变更

```
capabilities/workflow-conductor/
├── .claude-plugin/plugin.json       # 更新：新增 hooks 声明
├── .cursor-plugin/plugin.json       # 更新：新增 hooks 声明
├── hooks/
│   ├── hooks.json                   # 新增：Cursor 格式的 hooks 配置
│   ├── conductor-session-start.sh   # 新增：SessionStart hook 脚本
│   ├── conductor-stop.sh            # 新增：Stop hook 脚本（Claude Code 专用）
│   └── conductor-pre-compact.sh     # 新增：PreCompact hook 脚本
├── claude-code/
│   └── install.sh                   # 更新：安装时写入 hooks 配置到 settings.json
├── rules/
│   └── session-objective.md         # 不变
└── design-doc/
    └── (本文档)
```

### 3.4 脚本设计原则

- **共用脚本**: 三个 hook 用独立的 bash 脚本，通过 stdin 读取 JSON 输入
- **平台自适配**: 脚本通过检测 JSON 输入中的字段（如 `hook_event_name` vs 无此字段）判断运行在 Claude Code 还是 Cursor 环境，输出对应格式的 JSON
- **轻量快速**: 仅做文件扫描和文本拼接，不依赖外部工具（除 `jq`，考虑提供纯 bash fallback）
- **失败安全**: 脚本出错时 exit 0 + 空输出，不阻塞 agent 正常工作

## 4. 不在本次范围内

- **不修改协议本体**: `session-objective.md` 不需要因 hooks 的引入而改动。Hooks 是独立的保障层，协议本身的完整性不依赖 hooks 的存在
- **不做 PostToolUse hook**: 虽然可以在每次文件编辑后检查是否应更新 objective，但这会过于频繁，降低开发体验
- **不做 FileChanged hook**: 虽然 Claude Code 支持监听文件变更，但 objective 文件的变更监听会引入并发复杂性，暂不实现
