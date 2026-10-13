## Why

The closeout of `2026-10-13-restore-base-url-argv-for-remaining-continuations` recorded a
`product-improvement` follow-up: `get-log-briefs` accepts only `--project-path`, so a base-url
`exec` / `wait-for-exec` / `wait-for-log-pattern` `completed` response cannot offer a runnable
error-sweep invocation. It was kept as a candidate that omits `argv`. The CLI already resolves a
local log path for a base-url endpoint through `/health` (the Editor reports
`Application.consoleLogPath`), which is exactly what `get-log-source --base-url` uses, so the
remaining work is to route `get-log-briefs` through the same source resolution.

## What Changes

- Make `get-log-briefs` a selector-driven command: it accepts `--base-url` as an alternative to
  `--project-path`, using the same mutual exclusivity as the other selector-driven commands.
- Unify base-url log-source resolution: in base-url mode every log-related operation — the
  `log_range` a completed response advertises and `get-log-briefs` — SHALL resolve the effective
  log source from the addressed endpoint's reported console log path, falling back to the
  platform default only when the endpoint reports none. This fixes a latent inconsistency where
  base-url `log_range` offsets were captured from the platform default while `get-log-source`
  reported the Editor-named path.
- Reject `--unity-log-path` in base-url mode with the existing project-mode-only usage error, and
  report `no_observation_target` from `get-log-briefs` when the endpoint reports no usable source.
- No log content is transferred over the network; the endpoint is assumed to share the caller's
  filesystem, matching the existing base-url `log_range` contract.
- Restore the durable guidance requirement: a base-url completed response again carries a
  runnable `get-log-briefs` `argv` naming `--base-url`, `--range`, and `--levels error,warning`.
- Document the `--base-url` argument and the `no_observation_target` failure on the
  `get-log-briefs` help surface.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `formal-cli-contract`: adds `get-log-briefs` to the selector-driven commands and requires
  base-url log observation (advertised `log_range` and `get-log-briefs`) to resolve the
  endpoint-named log path before the platform default.
- `runtime-guidance`: removes the base-url carve-out from the success-path error-sweep
  requirement so a base-url completed response carries a complete `get-log-briefs` invocation.

## Impact

- Affected code: `cli/python/unity_puer_exec_surface.py` (parser selector args),
  `cli/python/unity_puer_exec_runtime.py` (`run_get_log_briefs`, `_resolve_log_path` base-url
  branch), `cli/python/help_surface.py` (help args, failure surface,
  `_PROJECT_PATH_ONLY_COMMANDS`), `tests/test_unity_session_cli.py`.
- Affected behavior: `get-log-briefs --base-url` works against a same-machine endpoint; base-url
  `log_range` and `get-log-briefs` resolve the same Editor-named log path; base-url completed
  guidance regains a runnable error sweep; `get-log-briefs` no longer counts as a
  project-path-only command.
- Affected validation: unit-only. No real-host requirement; the log source is mocked through the
  `/health` payload in tests.
