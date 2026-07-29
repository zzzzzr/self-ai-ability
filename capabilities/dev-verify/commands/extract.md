---
description: "将合并文件中的验证项提取为独立文件"
---

# /dev-verify:extract

将合并文件（含 `items` 字段）中的某个验证项提取为独立的 YAML 文件。

## 执行步骤

1. 读取 `.dev-verify/checks/*.yaml`，找出所有合并文件及其中的验证项
2. 列出可提取的项（名称 + 描述 + 所在合并文件），用户选择
3. 从合并文件的 `items` 列表中移除该项
4. 创建独立文件 `.dev-verify/checks/{name}.yaml`，写入提取出的验证项定义
5. 如果合并文件的 `items` 列表为空，提示用户是否删除该合并文件
6. 展示变更摘要供用户确认

## 参考

- 独立文件 vs 合并文件格式：`.dev-verify/DESIGN.md` §3.1
- 注册文件分层原则：`.dev-verify/DESIGN.md` §3.3
