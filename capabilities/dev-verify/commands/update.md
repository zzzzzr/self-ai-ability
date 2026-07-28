---
description: "修改已有的 dev-verify 验证项"
---

# /dev-verify:update

修改已注册的验证项配置。

## 执行步骤

1. 读取 `.dev-verify/checks/*.yaml`，列出所有已注册的验证项（名称 + 描述 + 所在文件）
2. 用户选择要修改的项
3. 展示该项的当前完整配置
4. 用户说明修改意图
5. 生成修改后的 YAML 定义，展示变更对比（修改前 vs 修改后）
6. 用户确认后写入

## 参考

- YAML 格式与字段定义：`.dev-verify/DESIGN.md` §3
