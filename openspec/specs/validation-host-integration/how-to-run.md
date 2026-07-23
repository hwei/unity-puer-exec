# Running Tests

## Test Layers

This repository has two distinct test layers:

**Mocked and helper-tool unit tests** (default):
```
python -m unittest tests.test_cleanup_validation_host_tool tests.test_cli_version tests.test_direct_exec_client tests.test_editor_log_isolation tests.test_openspec_backlog tests.test_openspec_change_meta tests.test_package_layout tests.test_prepare_validation_host_tool tests.test_unity_log_brief tests.test_unity_puer_session tests.test_unity_session tests.test_unity_session_cli tests.test_unity_session_modules
```
Cover parsing, payload contracts, status codes, packaging checks, OpenSpec tooling, and local validation-host helper logic. Run without Unity Editor or a validation-host project.

This is the same default suite executed by the repository's GitHub Actions unit-test workflow for pull requests and pushes to `main`.

**Real-host integration tests** (`tests/test_real_host_integration.py`):
Require a live Unity Editor and a prepared validation host project. Not executed unless explicitly enabled — they skip silently when prerequisites are not met.

## Running Real-Host Regression

Prerequisites:
- `UNITY_PROJECT_PATH` points to the validation host Unity `Project/` directory (set in environment or `.env`)
- Unity Editor is resolvable on this machine
- Validation host has been wired to the local package via `tools/prepare_validation_host.py`
- The helper output reports `"embedded_package_shadowing": false`. If it reports `true`, an immediate child of `Project/Packages/` declares `com.txcombo.unity-puer-exec` in its `package.json`, which can cause Unity to load that embedded copy instead of the repository-local package path in `manifest.json`; resolve or intentionally account for that before treating the run as evidence for current repository code. `"embedded_package_path"` names the first such directory and `"embedded_package_paths"` names all of them.

  Unity identifies an embedded package by the `name` declared in its `package.json`, not by the directory name. **Renaming the directory does not clear the shadow** — a directory renamed to `com.txcombo.unity-puer-exec.bak` is still loaded as `com.txcombo.unity-puer-exec`. Clearing the shadow requires **moving or removing the directory out of `Project/Packages/`** entirely.

Run command:
```
UNITY_PUER_EXEC_RUN_REAL_HOST_TESTS=1 python -m unittest tests.test_real_host_integration
```

### A concurrent unrelated Editor and the shared per-user log

A Unity Editor started without `-logFile` — which is every Editor opened from Unity
Hub — writes to the single per-user log at `%LOCALAPPDATA%\Unity\Editor\Editor.log`.
That file is per *user*, not per *project*, so two Editors open on two different
projects are bound to the same file and each one rotates and truncates it under the
other. Byte-offset observation across a file being rewritten by a second process is
meaningless: a `log_range` recorded moments earlier can point past the current end
of file, and content the validation host really did emit can be absent entirely.

The suite is safe to run in that condition because it brings the host up through a
**host-private log**. The CLI launches the validation host Editor with `-logFile`
pointing at `<project>/Temp/UnityPuerExec/Editor.log`, and that Editor reports the
same path back through `/health` as `console_log_path`, which the CLI ranks above
the platform default when resolving the effective log source. The path is recorded
in the session artifact at readiness, so individual cases observe it without each
supplying `--unity-log-path`. A development machine with several Unity projects
open at once is therefore a supported environment for real-host validation.

This does **not** extend to an Editor a human opened from Unity Hub and left running
on the host project. The CLI cannot change how that process was launched, so it will
still share the per-user log. Reporting `console_log_path` means the CLI at least
reads the file that Editor is genuinely writing to; if a second Hub-launched Editor
is open on another project, they still corrupt each other's offsets. Close the
unrelated Editor, or let the suite launch the host itself.

### Recognizing an invalidated log source

The symptom is a **log-observation wait that times out with no matched content** —
`wait-for-log-pattern` or `wait-for-result-marker` returning `unity_not_ready` after
its full timeout, while the exec that should have produced the output reports
success. `test_exec_checkpoint_observation_chain_against_real_host` is the case that
surfaces this first.

Distinguish an invalidated log source from a product regression before bisecting:

- Check `log_offsets_invalidated` in the failing response. Present means the supplied
  start offset was past the end of the observed log — the file was rotated or
  truncated, and the offsets stopped denoting the intended content.
- Run `unity-puer-exec get-log-source --project-path <host>` and read
  `result.resolution_tier`. `session_artifact` or `control_service` means the observed
  path was stated by an authority; `platform_default` means it was assumed, and an
  assumed path on a multi-Editor machine is very likely the wrong file.
- Compare `result.path` against the per-user `Editor.log`. If they are the same file
  and more than one `Unity.exe` is running, the observation target is shared.
- Grep the observed log for `[UnityPuerExec] Ready on port`. One occurrence with two
  live bridges means two Editors are writing to one file.

A wait timeout under any of those conditions is an invalidated log source, not a
regression in the CLI chain or the runtime.

### Control-port binding coverage prerequisites

Two cases in this suite assert control-port binding behavior and have extra
process-state prerequisites beyond the shared ones above:

- **Batch-mode service suppression**
  (`test_batch_mode_process_suppresses_control_service_against_real_host`):
  the host project must **not** be open in an interactive Editor. This case
  launches its own one-shot `Unity.exe -batchMode -nographics -quit` process,
  which needs the exclusive project lock; it `skip`s (does not fail) when any
  Unity process is already running. The suite's setUp force-stops the host
  Editor, so this normally holds — but if you keep the project open in your own
  Editor it will skip.
- **Occupied-preferred-port rollover**
  (`test_control_port_rolls_over_when_preferred_port_occupied_against_real_host`):
  needs an interactive Editor on the preferred control port (`55231`). The test
  is autonomous — it runs a retry-binder for `55231` and forces a domain reload
  (via `exec` of `UnityEditor.EditorUtility.RequestScriptReload()`, with a
  touched-script + `--refresh-before-exec` fallback) so the binder wins the
  port in the `Stop()`→`Start()` window. No operator step is required. It
  `skip`s when `55231` is held by an unrelated process at start.

## Result Interpretation

| Result | Meaning |
|--------|---------|
| `skip` | Prerequisites not met (env not set, `UNITY_PROJECT_PATH` missing, Unity Editor not found, or host manifest not wired). Not a product regression. |
| `fail` / `error` | Prerequisites were satisfied but the CLI chain, runtime, log observation, or assertion failed. This is a real-host regression. |

Mocked test passes do **not** substitute for real-host regression. They protect parsing, payload, and local contract logic only.
The default GitHub Actions workflow excludes `tests/test_real_host_integration.py` on purpose; real-host coverage remains a separate manual validation path.

## Current Coverage Chain

The real-host regression exercises this primary chain:

```
exec --project-path ... -> use log_range.start -> wait-for-result-marker -> wait-for-log-pattern --extract-json-group
```

For the full set of runtime validation requirements this covers, see [spec.md](spec.md).
