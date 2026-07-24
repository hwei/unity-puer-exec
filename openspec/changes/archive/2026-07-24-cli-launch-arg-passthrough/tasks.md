## 1. Launch-path plumbing

- [x] 1.1 Extend `launch_unity` to accept extra argv tokens, append them after CLI-owned args, and reject tokens that rebind `-projectPath`, `-logFile`, or `-unityPuerExecControl`.
- [x] 1.2 Parse ambient `UNITY_PUER_EXEC_UNITY_LAUNCH_ARGS` as a JSON array of strings; merge ambient then CLI-flag tokens with exact-token dedupe; surface parse failures as a usage/launch error with a machine-usable reason.
- [x] 1.3 Thread optional extra tokens from `ensure_session_ready` / `_launch_unity` so a cold launch receives them and an attach path ignores them without failing.

## 2. CLI surface

- [x] 2.1 Add repeatable `--unity-launch-arg` on project-scoped launch-owning commands (`exec`, and any other command that can cold-start Unity through `ensure_session_ready`).
- [x] 2.2 Restrict the flag to project-path mode (same boundary as `--unity-exe-path`); reject it with base-url.
- [x] 2.3 Update `help_surface` for the flag, the ambient variable, the CLI-owned-switch conflict rule, and the "launch only" scope.

## 3. Validation-host wiring

- [x] 3.1 Document `UNITY_PUER_EXEC_UNITY_LAUNCH_ARGS` in `.env.example` and in `validation-host-integration/how-to-run.md` next to the other real-host prerequisites.
- [x] 3.2 Confirm the real-host suite picks up the ambient variable through existing dotenv loading with no per-case flag changes (or make the minimum suite-side change if dotenv does not already reach `launch_unity`).

## 4. Tests and closeout

- [x] 4.1 Unit-test append order, conflict rejection, ambient JSON parse (valid, invalid, empty), flag+ambient merge/dedupe, and "tokens ignored on attach".
- [x] 4.2 Run the default unit suite and confirm no regressions.
- [x] 4.3 Run `openspec validate cli-launch-arg-passthrough`.
- [x] 4.4 Record apply closeout findings. Expected follow-up action (not this change's implementation): re-run `let-editor-publish-session-endpoint` task 8.7 full real-host suite with the ambient variable set, then archive that change.
