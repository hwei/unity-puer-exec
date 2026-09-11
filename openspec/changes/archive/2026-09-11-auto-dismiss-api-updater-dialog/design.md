## Context

See proposal.md for motivation.

The CLI already dismisses a small Windows dialog catalog from outside the Editor (`unity_modal_blockers.py`). Save-scene dialogs stay `modal_blocked` until `resolve-blocker`. Safe Mode is auto-dismissed and remapped to `unity_compile_error`. `wait-for-compile` and `wait_for_session` currently only poll `/health` (and log activity). Compiling `/health` omits `unity_pid`. Unity's `-disable-assembly-updater` (official Editor CLI docs) disables **AssemblyUpdater only**; ScriptUpdater still runs in an interactive Editor, so the source-file Yes/No dialog still appears.

The dialog blocks the Editor main thread. In-process C#/JS cannot dismiss it. Recovery must stay on the CLI Win32 path, like Safe Mode.

## Goals / Non-Goals

**Goals:**

- Auto-decline the ScriptUpdater consent dialog from every wait that can hang on it.
- Keep the original command's terminal status; attach a warning field when a dismiss happened in that request.
- Inject `-disable-assembly-updater` on CLI-owned cold launch without losing dialog-based detection.

**Non-Goals:**

- Auto-accepting API updates (Yes).
- Rewriting source or assemblies.
- Treating `[Assembly Updater] Ignoring assembly` as `api_updater_declined`.
- macOS/Linux click recovery (same as current modal catalog).
- Making this dialog a `resolve-blocker` citizen.

## Decisions

### D1: Identify by message body, click No via BM_CLICK

Match a visible Unity-owned window whose child static text contains the distinctive English sentence (`Some of this project's source files refer to API that has changed`). Title-only matching is too brittle (`API Updating` / `API Updater` / `Unity`). Click the button labeled `No` / `&No` with `BM_CLICK`. Do **not** send Enter: the default button is Yes and would rewrite sources.

Safe Mode keeps `keyboard`+Enter. This dialog is the opposite default.

### D2: Auto-recover in the wait loop, not after timeout

Poll and dismiss during `wait-for-compile` appear/settle, `wait_for_session`, and exec/wait-for-exec blocker checks. After a confirmed dismiss, continue waiting for `ready`. Repeat while the dialog reappears inside the same timeout budget (Unity can prompt per compilation unit).

If we only ran after settle timeout, the agent still burns the full wait and then retries into the same hang.

### D3: Warning is a sidecar field, not `status: "warning"`

`status: "warning"` is already the async-exec-result contract (`async_result_not_supported`). This change adds top-level `warning: "api_updater_declined"` and `warning_detail` on whatever status the command would have returned (`compile_settled`, `completed`, `unity_compile_error`, `running`, …). Exit code follows that primary status.

`get-blocker-state` does not report this dialog as `modal_blocked`. If it is visible, the CLI dismisses it when a wait/exec path is in flight; a pure query may still list it as a recovered type only if we need diagnostics, but the agent-facing exec path must not require `resolve-blocker`.

### D4: Inject `-disable-assembly-updater` as a launch default, not a reserved switch

Put the bare flag with other CLI-owned argv (before caller extras). Dedupe case-insensitively if the caller already passed it. Do **not** add it to `CLI_OWNED_UNITY_LAUNCH_SWITCHES`: that would usage-error hosts that already set it via `UNITY_PUER_EXEC_UNITY_LAUNCH_ARGS`.

Do not map the always-on Editor.log line `[Assembly Updater] warning: Ignoring assembly ...` to `api_updater_declined`. That line is a consequence of the flag, not of obsolete source APIs.

### D5: Compiling `/health` includes `unity_pid`

`--base-url wait-for-compile` often starts while already `compiling`, and that payload currently has no PID. Include `unity_pid` on bound compiling health when known (the server already reads it before branching). Project-path waits can keep using `session.unity_pid`.

No new HTTP endpoint.

## Risks / Trade-offs

- **[Risk] Localized Editor message text does not match the English fingerprint** → Mitigation: keep the English substring as the first matcher; if a real-host Chinese/JP Editor is observed, add those strings in a follow-up without changing the warning contract.
- **[Risk] Dialog is not a standard `#32770` / `Button` / `Static` tree** → Mitigation: spike EnumChildWindows dump in apply; fall back to scanning all child window text. If BM_CLICK fails, do not send Enter.
- **[Risk] `-disable-assembly-updater` consumes the next non-dash token as an assembly name** → Mitigation: inject the bare flag immediately after CLI-owned switches; following extras already start with `-` (e.g. `-force-gles30`).
- **[Risk] Attach to a Hub-launched Editor has no launch flag** → Mitigation: dialog dismiss still runs; warning still fires when the dialog is clicked.
- **[Trade-off] Declining leaves CS0618 / `(UnityUpgradable)` diagnostics** → That is intended; `get-compile-errors` / `get-compile-warnings` remain the compile surface. The new warning only means "we refused a rewrite."

## Migration Plan

No protocol break for ready health. Compiling health gains an optional `unity_pid` field; older CLIs ignore unknown keys. Older Editors without the field: project-path waits still have session PID; base-url waits skip click if PID is unknown rather than guessing a Unity process.

Rollback: revert catalog + launch inject; hosts that passed the flag themselves are unchanged.

## Open Questions

None that block specs. Exact window class/title is an apply-time spike; matching is specified as message-body fingerprint plus No button.
