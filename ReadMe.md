# unity-puer-exec

这个仓库承载 `unity-puer-exec` 的产品化开发工作。

产品边界：

- `unity-puer-exec/` 是正式 Unity package、正式 CLI、以及产品文档的 source of truth
- `c3-client-tree2/` 是验证宿主，不是正式产品源码仓库
- 正式 Unity package 源码现已位于 `packages/com.txcombo.unity-puer-exec/`
- 验证宿主应从干净基线出发，并通过本地 `manifest.json` 注入消费正式 package；辅助脚本见 `tools/prepare_validation_host.py`
- Unity 侧正式命名以 `UnityPuerExec` 为准，不加 `C3` 前缀
- 当前 `unity-puer-session` 仍可视为过渡入口；长期以 `unity-puer-exec` 为主入口

快速入口：

- repository context: `openspec/project.md`
- durable requirements: `openspec/specs/`
- active change work: `openspec/changes/`
- tests: `python -m unittest discover -s tests -p "test_*.py"`

目录概览：

- `AGENTS.md`: repository-local execution rules for agents
- `openspec/`: canonical governance, specs, and change artifacts
- `packages/com.txcombo.unity-puer-exec/`: formal Unity package home
- `tools/prepare_validation_host.py`: local validation-host manifest rewiring helper
- `tests/`: repository-level test entry points
- `cli/python/`: repo-owned Python CLI baseline location
