---
description: "初始化 dev-verify 验证配置"
---

# /dev-verify:init

初始化当前项目的 dev-verify 验证环境。

## 执行步骤

1. 检查 `.dev-verify/` 是否已存在：
   - 不存在 → 全新初始化，创建 `.dev-verify/checks/` 目录
   - 已存在 → 增量补充模式：检查哪些步骤尚未完成（如 `.gitignore` 未追加、checks/ 为空等），仅补充缺失项，不覆盖用户已有的注册文件
2. 检查 `.gitignore` 是否包含 `.dev-verify/`，未包含则追加
3. 将 DESIGN.md 放入 `.dev-verify/DESIGN.md`（已存在则更新）
4. 扫描项目中已有的规范资产，向用户建议可注册的验证项：
   - AGENTS.md / CLAUDE.md（NEVER 列表、架构约束、自检清单等）
   - `.cursor/rules/*.mdc`（编码规范类 rule）
   - wiki/ 目录（业务知识库）
   - 已有的 skill 文件
   - coding-profile catalog（如已安装）
5. 列出发现的资产和建议的注册方式（独立文件 vs 合并文件），等待用户确认
6. 用户确认后，按 `.dev-verify/DESIGN.md` §3 的 YAML 格式生成注册文件到 `.dev-verify/checks/`
7. 输出初始化结果摘要：创建了哪些文件、注册了哪些验证项

## 参考

- YAML 格式与字段定义：`.dev-verify/DESIGN.md` §3
- 目录结构：`.dev-verify/DESIGN.md` §6
