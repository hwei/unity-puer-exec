## Standard Prompt C: Basic C# Compile And Call

Use this prompt shape for the cleaner basic compile-and-verification task:

```text
现在要操作的 Unity 工程是 <PROJECT_PATH>。
请用 <CLI_ENTRY_PATH> 这个 CLI 在这个 Unity 工程里添加一个极简的 C# 静态函数，例如两个整数相加。
然后请只通过这个 CLI 完成必要的等待与验证，证明这个函数已经编译成功，并且后续 JS 执行确实能调用它并返回正确结果。
你只能依赖这个 CLI 自己提供的 help 来理解如何操作，不要读这个产品仓库的源码或测试。
完成后请自行验证结果。
```

### Target Intent

- The agent should handle a basic multi-step workflow that writes C# code and then verifies the result through a later CLI execution step.
- The workflow should test whether normal project-scoped `exec` use can absorb compile recovery without forcing host-side confirmation as the main path.
- The final verification should remain inside the CLI surface by confirming the returned result of a later JS-driven call into the new C# code.
- The task intentionally avoids Selection, menu execution, delayed editor callbacks, and log-only confirmation so it stays focused on the cleaner compile-and-call path.

### Prompt Stability Notes

- This is a new named standard prompt and does not replace the archived wording of Prompt A or Prompt B.
- Substitute only the concrete project path and CLI entry path.
- Do not add hidden hints such as specific bridge APIs, exact type names, or “use wait-for-exec”.
