## 1. Define Contract And Diagnostics

- [ ] 1.1 Decide the formal machine-readable shape for duplicate-launch conflict handling and reflect it consistently in CLI help and runtime responses
- [ ] 1.2 Identify the project-scoped evidence sources the CLI will trust before launching Unity again

## 2. Tighten Project-Scoped Launch Coordination

- [ ] 2.1 Refactor `ensure_session_ready(...)` so project-path workflows check project-scoped recovery evidence before calling `launch_unity(...)`
- [ ] 2.2 Ensure project-scoped `exec` reuses the same duplicate-launch avoidance path as `wait-until-ready`
- [ ] 2.3 Add stable diagnostics for launch-conflict or ownership-uncertain outcomes

## 3. Validate Duplicate-Launch Handling

- [ ] 3.1 Add mocked unit tests covering same-project already-open and launch-race branches
- [ ] 3.2 Add or extend real-host validation to cover rerunning readiness / exec while the target Editor is already open
- [ ] 3.3 Summarize whether any residual Unity single-instance edge cases still need follow-up after host validation
