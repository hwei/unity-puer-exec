# unity-puer-exec Skill

这个目录承载 `unity-puer-exec` 阶段二首批迁入的通用能力。

当前已迁入：

- 协议层 CLI
- Unity 会话层能力
- 会话层 CLI
- 对应实现

说明：

- 该 skill 仍面向外部 Unity 宿主工作，宿主项目当前放在 `../c3-client-tree2/`
- `unity_session.py` 已内置 Unity 版本解析与编辑器定位逻辑，不再依赖宿主仓库的 `Tools/python`
- repo 级测试入口现在位于 `../../../../tests/`
- 后续再补完整 `SKILL.md`、安装方式和 E2E 使用说明
