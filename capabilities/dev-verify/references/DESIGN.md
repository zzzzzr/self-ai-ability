# dev-verify 设计文档

> 创建时间: 2026-07-28
> 状态: 设计中

## 1. 概述

dev-verify 是一个 on-demand 的验证 skill，在代码实施完成后手动调用，验证增量代码是否符合各类要求和约束。

### 1.1 设计初衷

1. **释放 always-on 压力**：always-on rule 挤占上下文、分散模型注意力。将验证从"每次对话都检查"转为"实施后统一验证"，让模型开发时专注于开发。
2. **覆盖 rule 无法承载的验证面**：编码规范、agents.md、业务知识等不可能全部做成 always-on rule，但确实需要一个确定的验证点——这个验证点不会被模型能力升级吞噬。
3. **沉淀编码习惯和最佳实践**：某些业务场景有特定的编码风格和结构惯例，作为验证项注册到 dev-verify 中，既能保留这些经验，又不占开发时的上下文，避免后续维护时重复踩坑。

### 1.2 定位

- 适用于任何 AI 编码场景，不依赖特定开发流程
- 采用 on-demand 命令形式，不做 always-on rule
- 只验证增量代码，不验证存量

## 2. 子命令

| 命令 | 作用 |
|------|------|
| `init` | 初始化项目的验证配置目录和默认验证项，追加 `.dev-verify/` 到 `.gitignore` |
| `add` | 新增验证项（独立文件或追加到合并文件），生成后展示完整定义供用户确认再写入 |
| `update` | 修改已有验证项配置，修改后展示变更供用户确认 |
| `extract` | 将合并文件中的验证项提取为独立文件 |
| `verify` | 执行验证（核心命令） |

## 3. 验证项注册机制

### 3.1 注册文件格式（YAML）

#### 通用验证项（独立文件，跨项目复用）

```yaml
# coding-standards.yaml
name: coding-standards
description: 编码规范验证
priority: 1
mode: always
condition: ""
references:
  - path: .cursor/rules/coding-style.mdc
    type: file
  - path: .cursor/rules/data-security.mdc
    type: file
verify_focus: |
  检查代码是否违反编码规范中的硬约束（NEVER 列表）、
  命名规范、方法复杂度限制、数据安全要求等。
verify_mode: |
  严格遵守。NEVER 列表中的项为硬约束，违反即为问题。
```

#### 项目特定验证项（合并文件）

```yaml
# project-specific.yaml
items:
  - name: payment-reconciliation
    description: 对账模块编码习惯验证
    priority: 2
    mode: conditional
    condition: 改动涉及对账相关代码（recon/reconciliation）
    references:
      - path: .cursor/skills/reconciliation/SKILL.md
        type: file
    verify_focus: |
      验证对账相关代码是否遵循已沉淀的对账开发模式。
    verify_mode: |
      参考性遵守。优先遵循已有模式，但允许有充分理由的偏离，
      偏离时需在 findings 中说明理由。
```

### 3.2 字段说明

| 字段 | 必填 | 说明 |
|------|------|------|
| `name` | 是 | 验证项唯一标识，同时用于 findings 文件命名 |
| `description` | 是 | 一句话描述验证什么 |
| `priority` | 是 | 执行优先级，数字越小越先执行，同优先级并行 |
| `mode` | 是 | `always`（每次都执行）/ `conditional`（由子 agent 判断） |
| `condition` | 否 | `mode=conditional` 时的生效场景描述，供子 agent 判断 |
| `references` | 是 | 参考文档列表，子 agent 需读取的文件或目录 |
| `verify_focus` | 是 | 验证关注点：检查什么 |
| `verify_mode` | 是 | 验证方式/程度：以怎样的标准判断，不同验证项可以有不同的严格程度 |
| `parallel` | 否 | `true` 时该验证项内部可拆分为多个子 agent 并行验证（适用于 references 内容量大的情况）。默认 `false` |
| `scope_filter` | 否 | `true` 时子 agent 先基于改动内容筛选 references 中的相关部分，只验证相关内容，跳过无关部分以节省 token。默认 `false` |

### 3.3 注册文件分层

- **通用验证项**：每项一个独立 YAML 文件，可跨项目复用
- **项目特定验证项**：多项合并到一个 YAML 文件
- 使用者可自由决定组织方式，支持通过 `extract` 命令将合并文件中的项提取为独立文件
- 支持将现有 skill/rule/mdc 直接注册为验证项的 references

## 4. 执行流程

### 4.1 验证范围确定

用户提供 git diff / patch / commit 等确定改动内容。必要时允许模型自行确认改动范围（如读取当前分支的 diff）。

### 4.2 两阶段执行

#### Phase 1：并行验证

1. 主 agent 读取所有注册的验证项
2. 按优先级分组，同优先级的验证项并行启动子 agent
3. 每个子 agent 接收：改动内容 + 验证项定义（含 references、verify_focus、verify_mode）
4. 子 agent 自行判断是否适用（mode=conditional 时），不适用则快速退出不产出文件
5. `scope_filter=true` 时，子 agent 先基于改动内容筛选 references 中的相关部分（宁可多选不可漏选），只对相关部分执行验证
6. `parallel=true` 时，子 agent 可将验证拆分为多个子 agent 并行执行（如 wiki 按子域目录拆分）
7. 适用时执行验证，只有发现问题才写 findings 文件
8. 用户显式指定某验证项时，主 agent 标记"强制执行"，子 agent 跳过条件判断

#### Phase 2：汇总合成

1. 主 agent 读取所有 findings 文件
2. 结合对话上下文（本次改动的背景、目的）
3. 产出最终 verify-report.md

### 4.3 反向反馈

当验证发现约束条件本身有误（过时、矛盾、不合理）时，在 findings 中标记为"建议更新约束源"而非"代码违规"，形成 harness 飞轮。

## 5. 产物结构

```
.dev-verify/
└── <feature>/
    ├── findings/
    │   ├── coding-standards.md       # 按验证项 name 命名
    │   ├── wiki-business-logic.md
    │   └── ...                       # 只有发现问题的维度才有文件
    └── verify-report.md              # 最终汇总报告
```

- 产物目录不纳入 git 追踪（init 时追加 `.dev-verify/` 到 `.gitignore`）
- 按 feature 组织，便于与项目开发流程对应
- 中间产物（findings）保留，不自动清理
- 每个问题必须引用约束来源（文档路径 + 具体条目），解释为什么判定违规

## 6. 验证项配置目录

```
.dev-verify/
├── checks/                           # 验证项注册目录
│   ├── coding-standards.yaml         # 通用 - 独立文件
│   ├── agents-md.yaml                # 通用 - 独立文件
│   ├── wiki-compliance.yaml          # 通用 - 独立文件
│   └── project-specific.yaml         # 项目特定 - 合并文件
└── <feature>/                        # 验证产物（按 feature 组织）
    ├── findings/
    └── verify-report.md
```

## 7. 已知的验证维度候选

| 维度 | 参考源 | verify_mode 倾向 |
|------|--------|-----------------|
| 编码规范 | `.cursor/rules/*.mdc` | 严格遵守 |
| AGENTS.md / CLAUDE.md | 项目根目录 | 严格遵守（NEVER 列表）/ 参考遵守（建议项） |
| 业务知识库 | `wiki/` 目录 | 符合设计思路，不要求逐字一致 |
| 设计文档一致性 | 设计文档 / spec / plan | 实现与设计意图一致 |
| 架构约束 | AGENTS.md 架构规则 / check-architecture.sh | 严格遵守 |
| 子业务域最佳实践 | 各业务域 skill/文档 | 参考性遵守，允许有理由的偏离 |
| 高风险路径 | AGENTS.md 禁区列表 | 触碰时检查是否有配套（回滚方案/灰度等） |
| 自检清单 | AGENTS.md 改完代码必做 | 检查是否遗漏自检项 |

> 注：`docs/` 为废弃的旧知识库，不作为验证源。业务知识以 `wiki/` 为准。

## 8. 子 agent prompt 模板

```
你是 dev-verify 的验证子 agent。

## 你的验证项
名称: {name}
描述: {description}
验证关注点: {verify_focus}
验证方式: {verify_mode}
生效条件: {condition}
强制执行: {force_flag}

## 改动内容
{diff_content}

## 执行步骤

1. 判断是否适用：
   - 如果标记为"强制执行"，跳过此步直接验证
   - 如果 mode=always，直接验证
   - 如果 mode=conditional，根据改动内容和 condition 判断是否适用
   - 不适用时，输出"NOT_APPLICABLE"后退出，不写任何文件

2. 读取参考文档：
   {references 列表}
   - scope_filter={scope_filter}：如果为 true，先基于改动内容筛选参考文档中的相关部分，宁可多选不可漏选，跳过明确无关的内容
   - parallel={parallel}：如果为 true，可将验证拆分为多个子 agent 并行执行

3. 对照验证：
   按 verify_mode 描述的方式和程度，逐项检查改动内容是否符合参考文档的要求

4. 产出 findings：
   - 没有发现问题 → 输出"PASSED"，不写文件
   - 发现问题 → 写入 .dev-verify/{feature}/findings/{name}.md
   - 发现约束源本身有问题 → 标记为"建议更新约束源"
```

## 9. findings 文件格式

```markdown
# {验证项名称} 验证发现

## 问题列表

### 1. {问题标题}
- **严重程度**: 高 / 中 / 低
- **涉及文件**: {文件路径}:{行号}
- **问题描述**: {具体描述}
- **约束来源**: {参考文档路径} > {具体条目/章节}
- **约束原文**: {引用约束的原始表述}
- **建议修复**: {修复建议}

### 2. ...

## 约束源反馈（如有）

### 1. {约束源路径}
- **问题**: {约束本身的问题描述}
- **建议**: {修改建议}
```

## 10. verify-report 格式

```markdown
# {feature} 验证报告

> 验证时间: {timestamp}
> 改动范围: {diff 描述}

## 验证总览

| 状态 | 数量 |
|------|------|
| 通过 | X |
| 发现问题 | X |
| 不适用 | X |
| 总计 | X |

## 问题汇总（按严重程度排序）

### 高严重度

#### 1. [{验证项名}] {问题标题}
- **涉及文件**: ...
- **问题描述**: ...
- **约束来源**: ...
- **建议修复**: ...

### 中严重度
...

### 低严重度
...

## 约束源反馈

（当验证中发现约束本身有问题时列出，用于驱动 harness 飞轮）

### 1. {约束源路径}
- **问题**: ...
- **建议**: ...

## 通过的验证项

- {name}: {description}
- ...
```
