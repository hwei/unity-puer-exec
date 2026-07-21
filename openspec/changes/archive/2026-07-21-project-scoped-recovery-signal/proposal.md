## Why

`ensure_session_ready`'s `_has_recoverable_editor_signal` decides whether to wait for a recovering/starting Editor instead of launching a new one for the requested project. It bases that decision on `_list_unity_pids()` — every `Unity.exe` process on the host, not just ones belonging to the requested project. When an unrelated project's Editor is already running and the requested project has no session artifact, this misfires: `ensure_session_ready` enters a recovery wait for a recovery that will never happen, and (after `diagnose-exec-endpoint-misroute`'s fix stopped it from wrongly claiming the unrelated endpoint) simply times out without ever launching the requested project's own Editor. Confirmed live in that change's real-host validation (`openspec/changes/archive/2026-07-21-diagnose-exec-endpoint-misroute/results/validation-evidence.md`) and recorded there as a `product-improvement` follow-up candidate, not fixed by that change.

## What Changes

- Replace the system-wide `unity_pids` signal in `_has_recoverable_editor_signal` with a genuinely project-scoped signal: a non-blocking exclusive-lock probe against the requested project's own `Temp/UnityLockfile`. Unity holds this file locked for the entire time it has that exact project open (it is Unity's own mechanism for preventing the same project from being opened twice), so a failed lock-acquisition attempt means some process currently has *this* project open — independent of pid enumeration, independent of any time window.
- This replaces (not just supplements) the existing `_project_lock_details`/`fresh`-based idea considered and rejected during exploration: `fresh` is bounded by `PROJECT_RECOVERY_WINDOW_SECONDS` (30s), a crash-recovery window, not a liveness check — it would misfire on any Editor session open longer than 30 seconds. The lock-contention probe has no such window; it reflects live OS lock state at the moment of the check.
- Keep `artifact_pid_running` (the session artifact's own recorded `unity_pid`) as an additional recoverable signal alongside the lock probe — it is already project-scoped and cheaper than a lock probe when available.
- No change to `discover_project_endpoint`, `validate_endpoint_identity`, or the `wait_for_session` fix from `diagnose-exec-endpoint-misroute` — this change is scoped to the launch-vs-wait decision only.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `formal-cli-contract`: adds a new requirement alongside "Project-scoped commands validate control endpoint identity" — the decision to wait for a recovering Editor instead of launching a new one SHALL be based on a signal scoped to the requested project, not the presence of any Unity process on the host.

## Impact

- **Python CLI:** `cli/python/unity_session.py` (`_has_recoverable_editor_signal` and its call sites in `ensure_session_ready`); `cli/python/unity_session_process.py` (new project-lock lock-contention probe, Windows-only via `msvcrt.locking`, consistent with this module's existing Windows-only process helpers).
- **Tests:** new unit coverage for "unrelated project running, requested project's own lockfile is not held → launches instead of waiting"; existing recovery/launch-conflict test coverage in `tests/test_unity_session.py` must continue passing.
- **Origin:** follow-up from `diagnose-exec-endpoint-misroute` (see that change's design.md Decisions section and results/validation-evidence.md for the original finding).
