## Prompt B Rerun

Use this exact prompt shape for the rerun, substituting only the concrete project path and CLI entry path:

```text
现在要操作的 Unity 工程是 F:\C3\unity-puer-exec-workspace\c3-client-tree2\Project。
请用 F:\C3\unity-puer-exec-workspace\unity-puer-exec\cli\python\unity_puer_exec.py 这个 CLI 添加一个 Unity Editor 菜单命令。点击后它要 log 输出当前 Selection 的 GUID。
请自己完成必要的代码写入、等待 C# 编译、以及最终验证效果。
你只能依赖这个 CLI 自己提供的 help 来理解如何操作，不要读这个产品仓库的源码或测试。
完成后请自行验证这个菜单命令真的可用。
```

## Stability Rules

- Do not add hints such as `use exec`, `use --include-log-offset`, or `use wait-for-log-pattern`.
- Do not include repository paths other than the target project path and the CLI entry path.
- Keep the workflow goal unchanged so results remain comparable to the archived Prompt B baselines.
