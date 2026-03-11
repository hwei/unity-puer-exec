# unity-puer-exec

这个仓库承载 `unity-puer-exec` 阶段二的产品化开发工作。

当前包含：

- runtime implementation under `.claude/skills/unity-puer-exec/`
- repository-level docs under `docs/`
- repository-level tests under `tests/`

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
- `.claude/skills/unity-puer-exec/`: current runtime code
