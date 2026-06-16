## Why

The control-port binding behaviors fixed in `fix-control-port-bind-fallback` — rolling over to a later port when the preferred port is occupied (under Mono's `SocketException`), and skipping the listener in batch-mode subprocesses — were proven only by manual host inspection (`netstat`, worker logs, `/health`). Nothing in `tests/test_real_host_integration.py` exercises them, so a future refactor of `UnityPuerExecServer.Start()` could silently reintroduce the dead-fallback or worker-squatting bug without any automated signal. This was logged as a `validation-gap` follow-up at that change's closeout.

## What Changes

- Add a real-host regression that proves a **batch-mode Unity subprocess does not start the control service**: launch Unity with `-batchMode`, and assert its log contains the skip line and contains no `Ready on port` / `Failed to bind` line and binds no port in the control range.
- Add a real-host regression that proves **the interactive control service rolls over to a later port when the preferred port is already in use**, rather than failing the whole bounded scan.
- Keep both under the existing opt-in real-host gate (`UNITY_PUER_EXEC_RUN_REAL_HOST_TESTS`) so the default mocked/unit CI workflow is unaffected, and make them skip cleanly when prerequisites (Unity Editor, host project) are absent.

## Capabilities

### New Capabilities
<!-- None: this extends an existing validation capability. -->

### Modified Capabilities

- `validation-host-integration`: Add a requirement that the repeatable real-host validation workflow covers control-port binding behavior — both batch-mode service suppression and occupied-preferred-port rollover — as durable regression expectations alongside the existing CLI-workflow coverage.

## Impact

- Tests: `tests/test_real_host_integration.py` — new cases plus any small helper for launching a batch-mode Unity run and for occupying a loopback port during an interactive startup.
- Spec: `openspec/specs/validation-host-integration/spec.md` — one new requirement with scenarios.
- No product/runtime code changes; this is validation coverage only. Depends on the already-shipped behavior from `fix-control-port-bind-fallback` (released in v0.5.1).
