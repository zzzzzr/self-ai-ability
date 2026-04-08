# Capabilities

当前已内置 `example-skill` 和 `workflow-conductor` 两个 capability。

当你需要新增一个能力时，在这里新增一个目录，例如:

```text
capabilities/my-skill/
├── .claude-plugin/plugin.json
├── .cursor-plugin/plugin.json
└── skills/my-skill/SKILL.md
```

新增后，再把它登记到根目录的两个 `marketplace.json` 中即可。

注意：

- 不要在 capability 目录里放 `install.md`
- 这类"需要人工完成的安装后说明"统一放到 `docs/install/<capability-name>.md`
