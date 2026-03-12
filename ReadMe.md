# unity-puer-exec

这个仓库承载 `unity-puer-exec` 阶段二的产品化开发工作。

当前包含：

- the formal Unity package product line, targeting `com.c3.unity-puer-exec`
- the formal CLI product line, targeting `unity-puer-exec`
- transitional runtime implementation under `.claude/skills/unity-puer-exec/`
- repository-level docs under `docs/`
- repository-level tests under `tests/`

产品边界：

- `unity-puer-exec/` 是正式 Unity package、正式 CLI、以及产品文档的 source of truth
- `c3-client-tree2/` 是验证宿主，不是正式产品源码仓库
- 宿主侧当前的 `com.c3.unity-puer-exec.validation` 仍是过渡位置，后续会迁入本仓库并去掉 validation 命名
- 当前 `unity-puer-session` 仍可视为过渡入口；长期以 `unity-puer-exec` 为主入口

快速入口：

- workflow: `docs/workflow.md`
- active work: `docs/roadmap.md`
- current status: `docs/status.md`
- active decisions: `docs/decisions/`
- tests: `python -m unittest discover -s tests -p "test_*.py"`

目录概览：

- `AGENTS.md`: repository-local execution rules
- `docs/`: workflow, roadmap, status, decisions, and temporary plans
- `tests/`: repository-level test entry points
- `.claude/skills/unity-puer-exec/`: current transitional runtime code location
