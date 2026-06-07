# multi-project-sync

| 字段 | 值 |
|------|-----|
| type | script |
| version | 1.0.0 |

在多个项目副本（如 `for_git` / `for_hub`）之间保持环境一致。包含两个脚本，共用一份 `targets` 配置。

## 两个脚本的关系

| 脚本 | 角色 |
|------|------|
| `scripts/run-command.sh` | **通用引擎**：对 targets 中每个项目执行你传入的任意命令（`{dest}` 占位符） |
| `scripts/sync-plugins.py` | **内置操作**：对 targets 中每个项目**追加** `.cursor/.claude/settings.json` 的 plugins（不删除已有项） |

典型联动：先 `sync-plugins` 追加缺失的 plugins，再 `run-command.sh` 批量安装某个 capability。可用 `git diff` 确认仅有新增/更新、无删除。

## 首次配置

```bash
cp capabilities/multi-project-sync/config/sync-config.example.json \
   capabilities/multi-project-sync/config/sync-config.json
# 编辑 targets 列表
```

## 常用命令

```bash
# 批量执行安装命令
capabilities/multi-project-sync/scripts/run-command.sh \
  "./install.sh workflow-conductor --dest {dest} --force"

# 追加标准 plugins（已有 key 跳过，不删除目标里多余的 plugin）
python3 capabilities/multi-project-sync/scripts/sync-plugins.py \
  --from-file capabilities/multi-project-sync/config/plugins-standard.json

# 预览 plugins 变更
python3 capabilities/multi-project-sync/scripts/sync-plugins.py \
  --from-file capabilities/multi-project-sync/config/plugins-standard.json \
  --dry-run
```

## sync-plugins 选项

| 选项 | 作用 |
|------|------|
| `--from-file FILE` | 从 JSON 读取 plugins |
| `--from-project DIR` | 从某项目的 settings.json 读取 plugins |
| `--force` | 对已存在的 plugin key 更新值（默认跳过已有 key） |

默认**仅追加**：只添加 source 中有、目标中没有的 plugin key，**永不删除**目标里已有的 plugin。若 `git diff` 出现删除行，说明不是本脚本造成的。
| `--platform cursor/claude/both` | 同步平台（默认 both） |
| `--dry-run` | 预览变更 |
| `--exclude DIR` | 排除某个目标 |
| `--config FILE` | 指定 targets 配置（默认 `config/sync-config.json`） |

## 目录结构

```text
multi-project-sync/
├── config/
│   ├── sync-config.example.json
│   └── plugins-standard.json
└── scripts/
    ├── run-command.sh
    └── sync-plugins.py
```
