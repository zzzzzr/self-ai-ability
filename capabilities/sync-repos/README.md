# sync-repos

| 字段 | 值 |
|------|-----|
| type | script |
| version | 1.0.0 |

在一个父目录下维护多个 Git 子仓库时，批量执行 `git fetch origin` + pull。

## 首次配置

```bash
cp capabilities/sync-repos/config/sync-repos-config.example.json \
   capabilities/sync-repos/config/sync-repos-config.json
# 编辑 target、pull_mode、exclude
```

## 常用命令

```bash
# 使用 config 中的 target
capabilities/sync-repos/scripts/sync-repos.sh

# 临时指定 target 并追加排除
capabilities/sync-repos/scripts/sync-repos.sh \
  --target ~/Documents/for_hub --exclude foo,bar

# 预览
capabilities/sync-repos/scripts/sync-repos.sh --target ~/Documents/for_git --dry-run

# 覆盖 pull 策略（默认 rebase）
capabilities/sync-repos/scripts/sync-repos.sh --pull-mode ff-only
```

## 行为说明

- 只扫描 `target` 的**直接子文件夹**（一层）
- 非 Git 目录、排除项、隐藏目录计入 `skipped`
- `pull_mode` 支持 `rebase`（默认）、`ff-only`、`merge`
- pull 失败且处于 rebase 状态时自动 `git rebase --abort`
- 全部完成后输出「遇到问题的子目录」；有失败时退出码非 0

## 选项

| 选项 | 作用 |
|------|------|
| `--target PATH` | 覆盖 config 中的父目录 |
| `--pull-mode MODE` | `rebase` / `ff-only` / `merge` |
| `--exclude NAME` | 临时追加排除（与 config 取并集） |
| `--config FILE` | 指定配置文件 |
| `--dry-run` | 只打印计划执行的 git 命令 |

## 配置示例

```json
{
  "target": "~/Documents/for_git",
  "pull_mode": "rebase",
  "exclude": ["archived-demo"]
}
```

## 目录结构

```text
sync-repos/
├── config/
│   └── sync-repos-config.example.json
└── scripts/
    ├── sync-repos.sh
    └── sync-repos.py
```
