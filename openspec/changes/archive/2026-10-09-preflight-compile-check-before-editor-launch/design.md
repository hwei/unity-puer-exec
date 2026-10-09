## Context

`tests.test_real_host_integration` launches one interactive Editor per test class through
`_SharedRealHostDevice.setUpClass` / `_start_shared_host`. When the package does not
compile, that launch reaches the Editor's Safe Mode dialog and the suite cannot proceed
unattended.

Batch mode is the non-interactive path. It still compiles every assembly the Editor would
load, including the repository-local package injected through
`Project/Packages/manifest.json`, and it writes `error CS` lines to the log it is given.

## Goals / Non-Goals

**Goals:**
- Surface a package compile error as a fast, named real-host preflight failure before any
  interactive Editor launch.
- Keep the preflight out of the default (non-gated) unit-test run and skip cleanly when
  the host is not prepared.
- Reuse the existing host-resolution and `.env` launch-argument paths rather than adding a
  second way to locate the project or Unity.

**Non-Goals:**
- Replacing the interactive real-host run or the opt-in gate.
- Building/validating the package for release (that is the OpenUPM pipeline).
- Detecting compile errors produced only by optional build targets.

## Decisions

### D1. Preflight is a separate batch-mode launch, not a hook into the interactive run

The interactive launch cannot report a compile error to the suite because Safe Mode
intercepts it. A `Unity -batchMode -quit -nographics` invocation with a project-private
`-logFile` produces the diagnostics and exits deterministically. It runs the same import
and script-compilation pipeline, so it catches the exact class of failure that reached
Safe Mode.

### D2. Preflight runs once per suite invocation

`setUpClass` launches one interactive host per class. The preflight is not per class; it
runs once per process (module-level, or guarded by a module flag) so the added cost stays
a single batch launch regardless of how many classes run. This preserves the existing
"suite cost scales with cases, not host relaunches" property.

### D3. Failure is a parsed diagnostic, not a raw log dump

On a non-zero exit, the preflight parses `error CS` lines out of the batch log and reports
them as the failure detail. If the exit is non-zero with no `error CS`, it reports the
exit code and the log path so the caller can tell a compile failure from a launch failure.

### D4. Skip semantics match the existing gate

When the host project, Unity executable, or manifest is unavailable, the preflight is
skipped and the suite behaves as it does today (skip or run, per the existing gate). The
preflight never turns a skip into a failure.

## Open Questions

- Whether `-nographics` is safe on every developer machine that can run the interactive
  host, or whether it should be dropped when a graphics device is required for import.
