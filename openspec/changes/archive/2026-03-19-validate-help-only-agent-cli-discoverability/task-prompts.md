## Standard Prompt A: Scene Editing

Use this prompt shape for the simple task:

```text
现在要操作的 Unity 工程是 <PROJECT_PATH>。
请用 <CLI_ENTRY_PATH> 这个 CLI 在 `Assets/__AgentValidation/scene-editing-test.unity` 这个临时场景里创建一个 sphere。
你只能依赖这个 CLI 自己提供的 help 来理解如何操作，不要读这个产品仓库的源码或测试。
完成后请自行确认结果已经生效。
```

### Target Intent

- The agent should discover the primary execution workflow through CLI help.
- The agent should operate the real Unity Editor project, not invent a hypothetical command.
- The agent should verify that the sphere was actually创建在指定的临时场景中。
- The task intentionally avoids the unnamed active scene so validation does not depend on Unity-native save-scene modal behavior.

## Standard Prompt B: Code Change, Compile, and Verification

Use this prompt shape for the longer task:

```text
现在要操作的 Unity 工程是 <PROJECT_PATH>。
请用 <CLI_ENTRY_PATH> 这个 CLI 添加一个 Unity Editor 菜单命令。点击后它要 log 输出当前 Selection 的 GUID。
请自己完成必要的代码写入、等待 C# 编译、以及最终验证效果。
你只能依赖这个 CLI 自己提供的 help 来理解如何操作，不要读这个产品仓库的源码或测试。
完成后请自行验证这个菜单命令真的可用。
```

### Target Intent

- The agent should handle a multi-step workflow instead of a single fire-and-forget command.
- The agent should recover from the normal compile or readiness cycle through the CLI surface.
- The agent should prove the end result by running a real verification step, not by assuming the code compiled.

## Prompt Stability Rules

- Keep the goal wording stable across runs so results remain comparable.
- Substitute only the concrete project path and CLI entry path.
- Do not add hidden hints such as “use exec” or “you may need wait-for-result-marker”.
- If a future task variant is added, write it as a new named standard prompt instead of mutating Prompt A or Prompt B.
