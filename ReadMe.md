# unity-puer-exec

这个目录是 `unity-puer-exec` 阶段二的产品化开发仓库。

当前已完成的首批迁移内容：

- `.claude/skills/unity-puer-exec/cli.py`
- `.claude/skills/unity-puer-exec/unity_session.py`
- `.claude/skills/unity-puer-exec/unity_session_cli.py`
- `.claude/skills/unity-puer-exec/tests/`

当前约束：

- validation 相关的 Unity 宿主与 E2E 资产仍保留在验证宿主仓库 `../c3-client-tree2/`
- 本仓库内的 `unity_session.py` 已去除对宿主 `Tools/python` 的直接依赖
- Unity 工程路径解析优先级为：`--project-path` > `UNITY_PROJECT_PATH` > 当前工作目录
- repo 内 `.env` 记录当前验证宿主的 `UNITY_PROJECT_PATH`；相关操作前应先加载该环境变量
