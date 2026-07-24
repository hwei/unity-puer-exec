## Why

The CLI writes `Temp/UnityPuerExec/session.json` to record how to reach a project's Editor, and that record is a **claim the CLI makes about a process it does not own**. In the attach paths it fills `unity_pid` from `list_unity_pids()[0]` — the first `Unity.exe` in the machine-wide tasklist — while the ready `/health` payload it just received carries the correct pid and is never read (`unity_session.py:639`, `unity_session.py:382`). On a machine with several projects open that records an **unrelated project's pid**, which then drives `_artifact_pid_running`, the recovery signal, launch-conflict detection, and `ensure-stopped`. `ensure-stopped --immediate-kill` can therefore `taskkill /T /F` an Editor belonging to a different project.

`ensure-stopped` also answers the wrong question. Its spec scopes it to "a **recorded session PID** that is no longer running" (`formal-cli-contract`), while every caller needs "is any Editor still serving this project". Those diverge exactly when an Editor exists that the artifact does not know about, so `ensure-stopped` can report `stopped` while an Editor is live and answering. That is what let a real-host case attach to a Hub-launched Editor and observe the shared per-user log on 2026-07-23. In the artifact-absent branch it degrades the other way — `len(all Unity.exe) == 0` — so any unrelated Editor makes it report "not stopped" forever, contradicting `validation-host-integration`'s requirement that a machine running several Unity projects remain supported.

After `isolate-validation-host-editor-log`, every field the artifact holds is covered one-for-one by the running Editor's own state, and `console_log_path` was the last one missing. The artifact now records nothing the Editor cannot state about itself more accurately.

The remaining obstacle is that the control service starts implicitly and only in non-batch processes, so what a caller may assume differs per launch mode: a CLI-launched Editor gets an isolated log and a service, a Hub-launched Editor gets a service and a shared log, a batch process gets neither.

## What Changes

- The Unity bridge SHALL publish `Temp/UnityPuerExec/endpoint.json` when its control service starts, describing itself: `port`, `unity_pid`, `project_path`, `session_marker`, and `console_log_path`. The Editor writes it about itself, so every field is correct by construction, and it lives and dies with `Temp/`.
- The CLI SHALL discover a project's session from `endpoint.json` plus `Temp/UnityLockfile` instead of scanning the control-port range, and `session.json` is **removed** along with the CLI-side claims that populated it.
- Starting the control service becomes an **explicit opt-in**, uniform across CLI, batch-mode, and Hub launches: a command-line switch (process-lifetime) or an Editor menu action (session-lifetime, via `SessionState`). The menu action is deliberately **not** persisted.
- `ensure-stopped` SHALL decide from the published endpoint and the project lockfile rather than from a recorded pid or a machine-wide `Unity.exe` count.
- A project with no published endpoint SHALL produce a distinct status with actionable guidance rather than a silent attach to whatever answers the preferred port.
- An endpoint whose `console_log_path` is the platform default SHALL be reported as observation-degraded **before** the first observation, complementing the after-the-fact `log_offsets_invalidated` signal.
- **BREAKING** — the CLI no longer silently attaches to an Editor it did not launch and that did not opt in. Such a caller must either let the CLI launch the Editor, use the menu action, or drive the endpoint explicitly with `--base-url`.
- **BREAKING** — the control service no longer starts implicitly on Editor load. An interactive Editor opened from Unity Hub has no control service until it opts in.
- **BREAKING** — `Temp/UnityPuerExec/session.json` is no longer written or read.

## Capabilities

### New Capabilities

- `editor-session-discovery`: the Editor publishes its own endpoint at a deterministic project-scoped path, the CLI discovers sessions from that publication and the project lockfile, and control-service activation is explicit and uniform across launch modes.

### Modified Capabilities

- `project-control-endpoint`: the control service starts only on explicit opt-in, and publishes an endpoint description alongside `/health`.
- `formal-cli-contract`: log-source resolution drops the session-artifact tier; `ensure-stopped` is redefined in terms of a live project-owned endpoint; a new non-success status covers a project with no published endpoint.
- `editor-log-isolation`: the resolution tier list loses `session_artifact` and gains an a-priori degraded-observation signal.
- `validation-host-integration`: the real-host boundary is established from the published endpoint rather than from a recorded pid.

## Impact

- `packages/com.txcombo.unity-puer-exec/Editor/UnityPuerExecServer.cs`: opt-in gating for `StartServer`, command-line switch parsing, `SessionState`-backed menu opt-in, `endpoint.json` write on bind and removal on stop.
- `packages/com.txcombo.unity-puer-exec/Editor/` (new): menu action(s) for mid-session activation.
- `cli/python/unity_session_common.py`: `SESSION_RELATIVE_PATH` removed, endpoint path added.
- `cli/python/unity_session_logs.py`: artifact read/write removed; endpoint read; resolution tiers revised.
- `cli/python/unity_session.py`: the bulk of the work — `session_data` and `read_session_artifact` have ~85 references concentrated here; `validate_artifact_endpoint`, `_artifact_pid_running`, and the artifact-driven recovery branches are replaced by endpoint-driven equivalents.
- `cli/python/unity_session_process.py`: `ensure_stopped` decision rule; `launch_unity` passes the activation switch.
- `cli/python/unity_puer_exec_runtime.py` / `help_surface.py`: new status, guidance, and degraded-observation reporting.
- `tests/`: unit coverage for endpoint discovery, activation modes, and the revised stop rule; real-host confirmation across CLI, batch, and Hub launches.
