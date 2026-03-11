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
- 默认 `--project-path` 仍指向仓库根目录下的 `Project/`，当前进行宿主验证时应显式传入 `../c3-client-tree2/Project`
