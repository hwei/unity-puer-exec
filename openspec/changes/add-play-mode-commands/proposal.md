## Why

Agents that test autonomously enter and leave play mode all the time. Today the only way
to do that is an `exec` script that sets `EditorApplication.isPlaying`. That script only
*requests* the transition. Help tells the agent to request, confirm, and then wait,
so every agent rebuilds the same three-step sequence by hand, and the tree5 incident
shows how it goes wrong (see `surface-play-mode-compile-block`). Two related gaps make
it worse:

- Entering play mode with a compile-triggering change still pending traps the agent:
  it then runs stale code until it leaves play mode.
- An agent that drives the Editor alone is usually not the focused window. Unless
  `Application.runInBackground` is on, the game loop stalls as soon as the Editor loses
  focus, and play-mode tests hang or crawl.

A short `stop` command collides with the existing `ensure-stopped`, which closes the
Editor process. The two would sit next to each other in help and invite exactly the
wrong call, so `ensure-stopped` is renamed to `ensure-closed`. The old name stays as a
deprecated alias.

Inherited from `surface-play-mode-compile-block` (prerequisite): `compile_blocked`
reporting, the play-mode warning on `exec`, the "Script Changes While Playing" preference
in health, and the root cause of the "cannot stop play mode" report. That change's
interim `exec`-based continuation is replaced here by `stop`.

## What Changes

- **New commands `play`, `pause`, `stop`** in the "Primary Execution" group, with the
  standard `--project-path` / `--base-url` selectors. Each waits until the Editor
  *reaches* the requested state, not just until it is requested, and reports the final
  play state. All three are idempotent: a target already in the state returns
  `already_in_state`.
- **`play` resumes a paused Editor**, so no separate `resume` command is needed.
- **`play` settles pending code first.** In project mode it prepares the Editor like
  `exec`. If a compile-triggering change is pending, it runs the refresh and compile
  cycle before entering play mode, and returns `unity_compile_error` (exit 23) without
  entering play mode if compilation fails.
- **`play` forces `Application.runInBackground = true` by default** for the play
  session, without touching Player Settings. The response says so and names
  `--no-run-in-background` as the way to keep the project's setting.
- **`stop` leaves play mode and settles the deferred compile.** When a change was pending,
  it waits for the compile cycle that Unity starts on exit and reports the outcome, with
  a follow-up to `get-compile-errors` on failure.
- **Health reports the play state** (`edit`, `entering`, `playing`, `paused`, `exiting`),
  so the CLI and callers can observe transitions directly.
- **BREAKING (soft): `ensure-stopped` is renamed `ensure-closed`.** The behavior, result
  statuses, and exit codes are unchanged. `ensure-stopped` stays invocable as a
  deprecated alias, and its responses point to `ensure-closed`.
- The PlayMode help requirement changes: help presents `play` / `pause` / `stop` as the
  normal path. The asynchronous-request caveat stays only for scripts that change play
  state directly.

## Capabilities

### New Capabilities

- `play-mode-control`: the `play` / `pause` / `stop` commands, including waiting for the
  transition, idempotency, settling pending code before play and after stop, and
  `runInBackground` forcing.

### Modified Capabilities

- `formal-cli-contract`: the flat command tree adds `play`, `pause`, `stop`, and
  `ensure-closed`, with `ensure-stopped` as a deprecated alias. "Observation and stop
  commands keep their boundary" is restated for `ensure-closed`. "Help states that
  PlayMode transitions are asynchronous requests" now points to the new commands.
- `project-control-endpoint`: the health response exposes the Editor play state.

## Impact

- `cli/python/command_registry.py`: new commands, the rename, and alias handling.
- `cli/python/unity_puer_exec_surface.py`, `unity_puer_exec_runtime.py`,
  `help_surface.py`: parsers, runtimes, guidance, and help. The play pre-settle reuses
  the exec refresh/settle path.
- `cli/python/unity_session.py`, `unity_session_process.py`: rename references.
- `packages/com.txcombo.unity-puer-exec/Editor/UnityPuerExecServer.cs`,
  `UnityPuerExecProtocol.cs`: a play-control endpoint, play state in health, and
  `runInBackground` applied on `EnteredPlayMode`, persisted across a domain reload.
- Tests: `tests.test_unity_session_cli`, `tests.test_unity_session_modules`,
  `tests.test_real_host_integration` (rename plus new real-host play cases).
- Consumers: host-project skills and AGENTS files that call `ensure-stopped` keep
  working through the deprecated alias. No host-project document change is required:
  host docs deliberately delegate command discovery to `--help`, so they do not list
  command names and cannot drift when the CLI is upgraded.
- `surface-play-mode-compile-block` guidance: its `next_steps` switch to `stop`.
