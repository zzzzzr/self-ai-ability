# dev-verify

代码实施后的增量验证工具。通过 YAML 注册验证项，检查增量代码是否符合各类要求和约束（编码规范、AGENTS.md、业务知识库等）。

## 命令

| 命令 | 说明 | 触发方式 |
|------|------|----------|
| `/dev-verify:init` (`/dv:init`) | 初始化验证配置 | 显式或口语化 |
| `/dev-verify:add` (`/dv:add`) | 新增验证项 | 显式或口语化 |
| `/dev-verify:update` (`/dv:update`) | 修改验证项 | 显式或口语化 |
| `/dev-verify:extract` (`/dv:extract`) | 提取为独立验证项 | 显式或口语化 |
| `/dev-verify:verify` (`/dv:verify`) | 执行验证 | **仅显式调用** |

短命令通过 symlink 实现：`ln -s dev-verify .claude/commands/dv`

## 安装后目录

```
.dev-verify/
├── DESIGN.md                    # 设计文档（init 时自动放入）
├── checks/                      # 验证项注册（YAML）
│   ├── agents-md.yaml           # 示例：AGENTS.md 验证
│   └── project-specific.yaml    # 项目特定验证项（合并文件）
└── <feature>/                   # 验证产物（按 feature 组织）
    ├── findings/
    │   └── <check-name>.md      # 仅有问题时才产出
    └── verify-report.md         # 汇总报告
```

## 核心机制

- **注册制**：验证项通过 YAML 文件注册，支持独立文件和合并文件两种组织方式
- **子 agent 并行**：按优先级分组，同优先级的验证项并行分发给子 agent
- **只报问题**：通过的验证项不产出文件，只有发现问题才写 findings
- **增量验证**：只验证改动的代码，不验证存量
- **约束源反馈**：发现约束本身有问题时标记为"建议更新约束源"

## 文件说明

| 路径 | 说明 |
|------|------|
| `commands/*.md` | 各子命令的执行指令 |
| `references/DESIGN.md` | 共享设计文档（格式定义、模板、字段说明） |
| `examples/agents-md.yaml` | 示例验证项：基于 AGENTS.md 的通用验证 |
