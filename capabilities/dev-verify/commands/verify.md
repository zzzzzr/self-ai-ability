---
description: "执行增量代码验证（必须由用户显式调用）"
---

# /dev-verify:verify

对增量代码执行验证。此命令必须由用户显式调用，不自动触发、不主动建议执行。

## 执行步骤

### Step 1：确定改动范围

按以下优先级确定增量代码范围：
1. 用户在命令中指定了 git diff / patch / commit → 直接使用
2. 用户未指定 → 尝试 `git diff HEAD` 或 `git diff main...HEAD` 获取改动
3. 仍无法确定 → 询问用户

### Step 2：确定 feature 名称

用于组织产物目录。按以下优先级：
1. 用户在命令中指定了 feature 名称 → 直接使用
2. 从当前分支名推断
3. 询问用户

### Step 3：加载验证项

读取 `.dev-verify/checks/*.yaml` 下所有注册文件，解析为验证项列表。对于合并文件（含 `items` 字段），展开为独立验证项。

如果没有找到任何注册的验证项，终止执行并提示用户："当前验证项为空，请确认是否已通过 `/dev-verify:init` 或 `/dev-verify:add` 注册验证项。"

### Step 4：按优先级分组分发子 agent

1. 按 `priority` 字段分组
2. 从最高优先级（数字最小）开始，同优先级的验证项并行启动子 agent
3. 当前优先级的所有子 agent 完成后，再启动下一优先级
4. 每个子 agent 的 prompt 按 `.dev-verify/DESIGN.md` §8 的模板构造
5. 用户在命令中显式指定了某验证项时，标记"强制执行"，子 agent 跳过条件判断

### Step 5：汇总合成

所有子 agent 完成后：
1. 清理 `.dev-verify/{feature}/` 目录：删除旧的 findings/ 和 verify-report.md，确保产物完全反映本次验证结果
2. 写入本次产生的 findings 文件
3. 读取 `.dev-verify/{feature}/findings/` 下所有 findings 文件
4. 汇总统计：总验证项数、通过数、发现问题数、不适用数
5. 按严重程度排序问题
6. 汇总所有"约束源反馈"
7. 按 `.dev-verify/DESIGN.md` §10 的格式写入 `.dev-verify/{feature}/verify-report.md`
8. 向用户输出验证结果摘要

## 参考

- 两阶段执行流程：`.dev-verify/DESIGN.md` §4
- 子 agent prompt 模板：`.dev-verify/DESIGN.md` §8
- findings 文件格式：`.dev-verify/DESIGN.md` §9
- verify-report 格式：`.dev-verify/DESIGN.md` §10
- 产物结构：`.dev-verify/DESIGN.md` §5
