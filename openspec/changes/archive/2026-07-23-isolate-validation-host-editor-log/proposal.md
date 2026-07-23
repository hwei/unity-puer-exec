## Why

Log observation is a core CLI capability — `wait-for-log-pattern`, `wait-for-result-marker`, `get-log-briefs`, and every `log_range` byte offset are built on reading the Unity Editor log. That log is currently located by **guessing**: `unity_session_logs.default_editor_log_path()` hardcodes `~/AppData/Local/Unity/Editor/Editor.log`. Meanwhile the Unity bridge already caches `Application.consoleLogPath` — the authoritative path of the running Editor — and never exposes it. The half that knows stays silent; the half that acts guesses.

The guess is wrong whenever more than one Editor is open, which is normal on a development machine. Verified on 2026-07-23: two Editors (`c3-client-tree2`, the validation host, and an unrelated `c3-client-tree3`) were both running without `-logFile`, so both were bound to the same per-user `Editor.log`. The file the CLI read contained **zero** occurrences of the result marker the validation host had just logged, and one occurrence of `[UnityPuerExec] Ready on port` where two Editors should have produced two. `test_exec_checkpoint_observation_chain_against_real_host` fails reproducibly under this condition and was misfiled as flaky.

Byte-offset invalidation is also absorbed in silence. `read_editor_log_chunk` resets any `start_offset` beyond end-of-file to `0` and rescans, so a caller holding a `log_range` from before a rotation gets no signal that its offsets stopped meaning anything — the observed failure is a wait that times out with no explanation. Diagnosing the case above required a 37-minute stashed-baseline comparison that a single response field would have made unnecessary.

## What Changes

- Expose the bridge's own `Application.consoleLogPath` as `console_log_path` in the `/health` response, so the running Editor states where it writes instead of leaving the CLI to infer it.
- Make the bridge-reported path the preferred source in the CLI's effective-log-path resolution, ahead of the platform-default guess. Explicit `--unity-log-path` and the session artifact continue to take precedence, so no existing caller changes behavior.
- Default launch-driven project-scoped sessions to a project-local Unity log under the project's `Temp/` directory, so an Editor the CLI starts never shares the per-user `Editor.log` with an unrelated Editor. `--unity-log-path` continues to override.
- Report log rotation or truncation instead of silently rescanning: when an observation's `start_offset` exceeds the current end of file, the response SHALL carry an explicit indication that the offsets were invalidated.
- Record in `validation-host-integration/how-to-run.md` that a concurrently running unrelated Unity Editor invalidates real-host log observation unless the host has an isolated log, and that the isolated-log default is what makes the suite safe to run on a shared development machine.
- **BREAKING** for a caller that both (a) relies on the CLI launching Unity for it and (b) reads the per-user `Editor.log` directly by path rather than through `get-log-source`: launch-driven sessions now write to a project-local log. Callers using `get-log-source` or the session artifact are unaffected.

## Capabilities

### New Capabilities

- `editor-log-isolation`: the bridge states its own log path, the CLI prefers that statement over a platform guess, launch-driven sessions get a project-private log, and offset invalidation is reported rather than absorbed.

### Modified Capabilities

- `project-control-endpoint`: the health identity requirement is extended to include the Editor's own console log path.
- `formal-cli-contract`: log-source resolution gains the bridge-reported path as a precedence tier above the platform default, and `get-log-source` reports which tier produced the answer.
- `validation-host-integration`: real-host validation requires an isolated host log so a concurrent unrelated Editor cannot invalidate observation.

## Impact

- `packages/com.txcombo.unity-puer-exec/Editor/UnityPuerExecServer.cs`: publish `cachedConsoleLogPath` through health handling.
- `packages/com.txcombo.unity-puer-exec/Editor/UnityPuerExecProtocol.cs`: `console_log_path` in `BuildHealthResponseJson`.
- `cli/python/unity_session_logs.py`: `resolve_effective_log_path` precedence; rotation detection in `read_editor_log_chunk`.
- `cli/python/unity_session.py`: thread the health-reported path into session construction and the session artifact.
- `cli/python/unity_session_process.py` / `unity_session.py`: default launch log path under the project's `Temp/`.
- `cli/python/help_surface.py`: `get-log-source` and `--unity-log-path` help text for the new precedence.
- `openspec/specs/validation-host-integration/how-to-run.md`: concurrent-Editor prerequisite and isolated-log rationale.
- `tests/`: unit coverage for precedence and rotation reporting; real-host confirmation that the host log is project-local and that observation survives a concurrent unrelated Editor.
