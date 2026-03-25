# unity-puer-exec

这个仓库承载 `unity-puer-exec` 的产品化开发工作。

产品边界：

- `unity-puer-exec/` 是正式 Unity package、正式 CLI、以及产品文档的 source of truth
- `c3-client-tree2/` 是验证宿主，不是正式产品源码仓库
- 正式 Unity package 源码现已位于 `packages/com.txcombo.unity-puer-exec/`
- 验证宿主应从干净基线出发，并通过本地 `manifest.json` 注入消费正式 package；辅助脚本见 `tools/prepare_validation_host.py`
- Unity 侧正式命名以 `UnityPuerExec` 为准，不加 `C3` 前缀
- 当前 `unity-puer-session` 仍可视为过渡入口；长期以 `unity-puer-exec` 为主入口
- 兼容入口与迁移辅助面应保持瘦包装性质，不应继续承载新的正式能力或独立工作流

快速入口：

- repository context: `openspec/config.yaml`
- durable requirements: `openspec/specs/`
- active change work: `openspec/changes/`
- tests: `python -m unittest discover -s tests -p "test_*.py"`

测试分层：

- 常规仓库测试: `python -m unittest discover -s tests -p "test_*.py"`
- 这组测试默认覆盖 mocked unit / CLI contract / helper 逻辑
- `tests/test_real_host_integration.py` 默认不会真正执行真实宿主链路；未显式开启时会以 `skip` 结束

真实宿主回归：

- 前提:
  `UNITY_PROJECT_PATH` 指向验证宿主 Unity `Project` 目录
- 前提:
  本机可解析 Unity Editor 路径，且宿主可通过 `tools/prepare_validation_host.py` 完成本地 package 注入
- 运行:
  `UNITY_PUER_EXEC_RUN_REAL_HOST_TESTS=1 python -m unittest tests.test_real_host_integration`
- 当前真实宿主回归覆盖一条主链路:
  `wait-until-ready -> exec --include-log-offset -> wait-for-result-marker -> wait-for-log-pattern --extract-json-group`

结果判读：

- `skip`:
  真实宿主回归未开启，或 `UNITY_PROJECT_PATH` / Unity Editor / 宿主 manifest 等前置环境不满足；这不算产品回归失败
- `fail` / `error`:
  在前置环境已满足后，CLI 链路、宿主运行时、日志观测或断言失败；这算真实宿主回归失败
- 常规 mocked 测试通过，不能替代真实宿主回归；它们主要保护解析、payload、状态码和本地 helper 合同

目录概览：

- `AGENTS.md`: repository-local execution rules for agents
- `openspec/`: canonical governance, specs, and change artifacts
- `packages/com.txcombo.unity-puer-exec/`: formal Unity package home
- `tools/prepare_validation_host.py`: local validation-host manifest rewiring helper
- `tests/`: repository-level test entry points
- `cli/python/`: repo-owned Python CLI baseline location
