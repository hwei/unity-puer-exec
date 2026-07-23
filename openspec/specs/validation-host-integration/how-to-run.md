# Running Tests

## Test Layers

This repository has two distinct test layers:

**Mocked and helper-tool unit tests** (default):
```
python -m unittest tests.test_cleanup_validation_host_tool tests.test_cli_version tests.test_direct_exec_client tests.test_openspec_backlog tests.test_openspec_change_meta tests.test_package_layout tests.test_prepare_validation_host_tool tests.test_unity_log_brief tests.test_unity_puer_session tests.test_unity_session tests.test_unity_session_cli tests.test_unity_session_modules
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
