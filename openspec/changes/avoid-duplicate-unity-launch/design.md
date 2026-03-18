## Context

当前项目级启动逻辑主要在 Python session/runtime 层完成。`ensure_session_ready(...)` 会先探测 `/health`，再基于 `tasklist` 中是否存在任意 `Unity.exe` 进程决定“等待现有进程恢复”还是“直接启动新的 Unity”。这对“已经有 Unity 打开”提供了粗粒度保护，但它没有确认该进程是否就是目标项目，也没有覆盖“检查通过到实际 Popen 之间出现新实例”的竞态窗口。

真实宿主验证和人工观察已经暴露了一个实际症状：当同一项目已在 Unity Editor 中打开时，CLI 仍可能尝试再次启动同项目，最终落到 Unity 原生的单实例冲突对话框。这个行为既不稳定，也不适合机器分支。

## Goals / Non-Goals

**Goals:**

- 让项目级 `wait-until-ready` 与 `exec` 在同项目已开或恢复中的场景下避免盲目二次启动。
- 让无法安全恢复或确认实例归属的情况表现为 machine-readable 的 CLI 状态，而不是 Unity 原生弹框。
- 把启动协调逻辑建立在项目级证据上，而不是只看全局 `Unity.exe` 进程数。
- 为真实宿主增加覆盖，证明已有 Editor 打开时主链路仍可预测。

**Non-Goals:**

- 不重做 Unity 侧 HTTP runtime 协议。
- 不引入跨机器或跨用户的分布式锁。
- 不承诺识别本机上所有 Unity 进程和所有项目之间的绝对映射；只解决仓库拥有的项目级 CLI workflow。

## Decisions

### Decision: 先使用项目级恢复证据，再决定是否 launch

项目级路径在调用 `launch_unity(...)` 前，应优先检查与目标项目相关的证据：session artifact、最近健康探测、以及目标项目在恢复窗口内的可用性。只有在这些证据都不足以证明“已有实例正在服务或可恢复”时，才允许新的 launch 尝试。

Alternative considered: 继续沿用“有无任意 Unity.exe”作为 gate。Rejected，因为它只能避免最粗糙的并发启动，不能识别目标项目，也解释不了同项目对话框。

### Decision: 把重复启动冲突归一成 machine-readable 状态

当 CLI 无法确认当前项目是否已被现有 Editor 占用，或检测到启动后出现同项目冲突时，应返回显式 machine-readable 结果，而不是把 UX 留给 Unity 的模态对话框。返回形态可以是新的 formal non-success 状态，也可以是现有错误模型下新增稳定 `error` 值，但必须能让调用方分支。

Alternative considered: 仅在帮助文本中提示“不要重复打开同项目”。Rejected，因为这不能保护自动化，也不能解决 real-host 回归里的不稳定行为。

### Decision: 项目级 `exec` 复用与 `wait-until-ready` 相同的启动协调

项目作用域 `exec` 已经允许隐式准备 Unity，因此它和 `wait-until-ready` 必须共享同一套启动冲突处理，不允许一个命令有保护、另一个命令仍然会触发重复启动。

Alternative considered: 只修 `wait-until-ready`。Rejected，因为真实 workflow 往往由 `exec --project-path` 直接触发准备。

### Decision: 真实宿主验证增加“已有 Editor”回归场景

除了现有冷启动链路，还需要补一个 real-host 场景：先确保目标项目的 Editor 已经打开，再重新执行 readiness 或 exec，验证 CLI 会恢复或复用，而不是再次发起冲突 launch。

Alternative considered: 只补 mocked 单测。Rejected，因为这次问题本身就是在真实 Unity 单实例行为下暴露的。

## Risks / Trade-offs

- [Risk] 项目级归属证据仍然不完美，某些边界场景可能无法完全确认现有 Editor 是否就是目标项目。 -> Mitigation: 将“不确定”显式归一为 machine-readable 非成功状态，而不是继续盲目 launch。
- [Risk] 更保守的启动策略可能让某些原本“碰巧能用”的场景变成显式失败。 -> Mitigation: 把状态设计成可分支、可诊断，并补充帮助与测试。
- [Risk] 真实宿主回归更依赖本机 Unity 状态，可能带来时序抖动。 -> Mitigation: 让测试步骤先显式准备“已有 Editor”状态，再验证后续命令，而不是依赖偶发条件。

## Migration Plan

1. 明确 formal CLI 对“重复启动冲突”的 machine-readable 行为。
2. 在 session/runtime 层引入项目级启动前检查和 launch 后冲突识别。
3. 让 `wait-until-ready` 与项目级 `exec` 共用该逻辑。
4. 补 mocked 单测与 real-host 回归。
5. 通过真实宿主验证后，再考虑是否把旧的粗粒度 `tasklist` 逻辑进一步收敛。

## Open Questions

- 重复启动冲突更适合表现为新的 top-level `status`，还是保留现有退出码模型、只增加稳定 `error` 值？
- 除 session artifact 外，是否需要额外的项目级本地锁文件来缩小 `check -> launch` 竞态窗口？
