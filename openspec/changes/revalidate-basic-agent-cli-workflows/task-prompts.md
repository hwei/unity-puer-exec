## Standard Prompt A: Scene Editing

Use this prompt exactly for the simple task, substituting only the concrete paths:

```text
现在要操作的 Unity 工程是 <PROJECT_PATH>。
请用 <CLI_ENTRY_PATH> 这个 CLI 在 `Assets/__AgentValidation/scene-editing-test.unity` 这个临时场景里创建一个 sphere。
你只能依赖这个 CLI 自己提供的 help 来理解如何操作，不要读这个产品仓库的源码或测试。
完成后请自行确认结果已经生效。
```

## Standard Prompt B: Code Change, Compile, And Verification

Use this prompt exactly for the longer task, substituting only the concrete paths:

```text
现在要操作的 Unity 工程是 <PROJECT_PATH>。
请用 <CLI_ENTRY_PATH> 这个 CLI 添加一个 Unity Editor 菜单命令。点击后它要 log 输出当前 Selection 的 GUID。
请自己完成必要的代码写入、等待 C# 编译、以及最终验证效果。
你只能依赖这个 CLI 自己提供的 help 来理解如何操作，不要读这个产品仓库的源码或测试。
完成后请自行验证这个菜单命令真的可用。
```

## Stability Rules

- Preserve the goal wording exactly so this round remains comparable with the archived baseline runs.
- Substitute only `<PROJECT_PATH>` and `<CLI_ENTRY_PATH>`.
- Do not add maintainer hints such as recommended commands or workflow suggestions.
- Run Prompt A and Prompt B sequentially against the same host project, not in parallel.
