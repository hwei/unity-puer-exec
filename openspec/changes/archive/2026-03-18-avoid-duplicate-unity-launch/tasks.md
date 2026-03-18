## 1. Define Contract And Diagnostics

- [x] 1.1 Decide the formal machine-readable shape for duplicate-launch conflict handling and reflect it consistently in CLI help and runtime responses
- [x] 1.2 Identify the project-scoped evidence sources the CLI will trust before launching Unity again

## 2. Tighten Project-Scoped Launch Coordination

- [x] 2.1 Refactor `ensure_session_ready(...)` so project-path workflows check project-scoped recovery evidence before calling `launch_unity(...)`
- [x] 2.2 Ensure project-scoped `exec` reuses the same duplicate-launch avoidance path as `wait-until-ready`
- [x] 2.3 Add stable diagnostics for launch-conflict or ownership-uncertain outcomes

## 3. Validate Duplicate-Launch Handling

- [x] 3.1 Add mocked unit tests covering same-project already-open and launch-race branches
- [x] 3.2 Add or extend real-host validation to cover rerunning readiness / exec while the target Editor is already open
- [x] 3.3 Summarize whether any residual Unity single-instance edge cases still need follow-up after host validation

## Residual Notes

- Project-scoped launch coordination now prefers session artifacts, Unity's project-local lockfile, and repo-owned launch claims before any new launch attempt.
- Real-host validation confirmed repeated `wait-until-ready` and project-scoped `exec` can reuse an already-open editor without treating the Unity-native duplicate-open dialog as the primary machine outcome.
- A residual edge remains when a human or foreign launcher mutates the target project outside repo-owned coordination and without a stable lock/service window; the current implementation intentionally fails conservatively with machine-readable launch ownership diagnostics instead of blindly launching again.
