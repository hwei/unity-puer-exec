## Why

项目级 `wait-until-ready` / `exec` 目前只做粗粒度的 `Unity.exe` 进程探测，然后在不确定场景下直接再次启动 Unity。真实宿主验证里已经出现过 “Unity Editor 已经打开，不能再次打开” 的原生对话框，这说明当前产品对同项目已开和启动竞态的处理还不够稳。

## What Changes

- 为项目级启动路径补上“同项目已开 / 正在恢复 / 启动竞态”识别，不再仅靠全局 `Unity.exe` 进程存在与否决定是否二次启动。
- 在无法安全接管或确认同项目实例时，返回 machine-readable 的可分支状态，而不是把行为退化成 Unity 原生弹框。
- 收紧 `wait-until-ready` 与项目作用域 `exec` 的启动协调逻辑，优先复用已存在服务、现有会话 artifact、以及同项目恢复窗口。
- 增加真实宿主验证，覆盖“Editor 已开时再次走 readiness / exec” 的关键链路。

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `formal-cli-contract`: 项目级 readiness / exec 需要对同项目已开和重复启动冲突提供可预期的 machine-readable 行为。
- `validation-host-integration`: 真实宿主验证需要覆盖“已有 Unity Editor 打开时再次调用 CLI”的回归场景。

## Impact

- `cli/python/unity_session.py`
- `cli/python/unity_session_process.py`
- `cli/python/unity_session_wait.py`
- `tests/test_unity_session*`
- `tests/test_real_host_integration.py`
- 真实宿主启动与恢复工作流
