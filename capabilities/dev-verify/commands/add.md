---
description: "新增 dev-verify 验证项"
---

# /dev-verify:add

新增一个验证项到 `.dev-verify/checks/`。

## 执行步骤

1. 与用户确认以下信息：
   - 验证什么（verify_focus）
   - 参考哪些文档（references）
   - 以什么方式/程度验证（verify_mode）
   - 生效条件（mode: always / conditional）
   - 是否需要选择性验证（scope_filter）
   - 是否需要内部并行（parallel）
   - 放入独立文件还是追加到已有合并文件
2. 按 design.md §3 的格式生成完整的 YAML 定义
3. 展示给用户确认
4. 用户确认后写入文件：
   - 独立文件：`.dev-verify/checks/{name}.yaml`
   - 合并文件：追加到指定的 `.dev-verify/checks/{filename}.yaml` 的 `items` 列表

## 参考

- YAML 格式与字段定义：`.dev-verify/DESIGN.md` §3
- 验证维度候选：`.dev-verify/DESIGN.md` §7
