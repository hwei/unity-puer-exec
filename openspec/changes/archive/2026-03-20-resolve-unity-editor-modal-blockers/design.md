## Context

`handle-unity-editor-modal-dialog-blockers` established two facts:

- project-scoped `exec` and `wait-for-exec` can detect supported Unity-native save dialogs on Windows and report `status = "modal_blocked"`
- the blocked exec request remains associated with its original `request_id`, so recovery should continue through `wait-for-exec` instead of resubmitting `exec`

That leaves a narrow but important follow-up: provide a repository-owned way to cancel the supported blockers without promising broad UI automation.

## Goals / Non-Goals

**Goals:**
- Add a project-scoped command that can cancel the supported Unity save-scene blockers on Windows.
- Keep the contract machine-usable and explicit when no supported blocker is present or when cancellation cannot be confirmed.
- Preserve the existing execution ownership model: resolution does not rerun or replace the blocked exec request.

**Non-Goals:**
- Do not support `save`, `don't save`, or arbitrary file-picker automation in the first version.
- Do not add blocker resolution to `base-url` mode.
- Do not broaden dialog support beyond the two blockers already covered by detection.
- Do not auto-resume `exec`; callers remain responsible for subsequent `wait-for-exec` or `get-blocker-state` calls.

## Decisions

### Decision: Introduce a dedicated `resolve-blocker` command
Resolution should be an explicit operator or caller action, separate from blocker detection and separate from `exec`.

Rationale:
- resolution is side-effecting and should not happen implicitly during detection or normal execution polling
- the caller can decide whether it wants a human to intervene or whether machine-issued cancel is acceptable

Alternative considered:
- Auto-dismiss blockers whenever detection succeeds. Rejected because it hides a state transition that callers may need to control.

### Decision: First version supports only `--action cancel`
The first supported action should be `cancel` for the already-detected save-scene dialogs.

Rationale:
- `cancel` is the safest shared behavior across both supported dialogs
- adding `save` or `don't save` would require stronger guarantees about path selection and user intent

### Decision: Keep resolution host-side and Windows-only
Resolution should stay in the Python host layer and reuse Win32 window enumeration plus targeted button interaction.

Rationale:
- the Unity Editor main thread may be blocked by the modal, making Unity-side resolution unreliable
- the existing detector already identifies the target dialogs from the host side on Windows

Alternative considered:
- Ask Unity-side code to dismiss the dialog. Rejected because that path depends on the same blocked UI thread.

### Decision: Confirm resolution by observing dialog disappearance
After issuing the cancel action, the CLI should short-poll for the target dialog to disappear before returning success.

Parameters:
- fixed poll interval: `100ms`
- fixed timeout: `1500ms`

Rationale:
- disappearance is the narrowest reliable confirmation the first version can observe
- the timeout should be internal, not caller-configurable

Alternative considered:
- Return success immediately after issuing the click. Rejected because it would hide common Win32 interaction failures.

### Decision: Return blocker `type` but omit `scope` in resolution results
Resolution results should include the resolved blocker type, but not the detection-time `scope`.

Rationale:
- detection uses `scope` to explain where the blocker was observed
- resolution is an independent command, so `scope = "exec"` would mix execution context into the resolution outcome itself

### Decision: Treat multiple matches as a hard failure
If more than one supported blocker dialog is detected, the command should fail without acting.

Rationale:
- first version should prefer no-op over ambiguous UI interaction
- multiple supported dialogs should be exceptionally rare and are safer to escalate to manual handling

## Runtime Shape

The first version command surface should be:

```text
unity-puer-exec resolve-blocker --project-path <path> --action cancel
```

Expected success payload:

```json
{
  "ok": true,
  "status": "completed",
  "result": {
    "status": "resolved",
    "action": "cancel",
    "blocker": {
      "type": "save_scene_dialog"
    }
  }
}
```

Expected no-target payload:

```json
{
  "ok": false,
  "status": "no_supported_blocker"
}
```

Expected resolution failure payload:

```json
{
  "ok": false,
  "status": "resolution_failed",
  "blocker": {
    "type": "save_modified_scenes_prompt"
  },
  "action": "cancel",
  "error": "click_not_confirmed"
}
```

Expected unsupported-operation payload:

```json
{
  "ok": false,
  "status": "unsupported_operation",
  "error": "windows_project_path_required"
}
```

## Error Surface

The first version should keep the structured `error` set intentionally small:

- `windows_project_path_required`
- `multiple_supported_blockers`
- `cancel_control_not_found`
- `click_not_confirmed`

Other implementation details may still appear in prose diagnostics or logs, but machine-branchable callers should only rely on the stable `status` and `error` values above.

## Caller Flow

The intended recovery flow for blocked exec work is:

1. `exec` or `wait-for-exec` reports `modal_blocked`
2. caller optionally confirms with `get-blocker-state`
3. caller invokes `resolve-blocker --action cancel`
4. if resolution succeeds, caller continues waiting on the original `request_id` with `wait-for-exec`

The caller must not resubmit the blocked `exec` request as a substitute for resolution.

## Risks / Trade-offs

- [Win32 button interaction can be brittle across localized shells] -> keep the supported dialog set narrow and validate against the repository-owned host environment first.
- [Cancel may lead the blocked exec request to fail in different ways after the dialog closes] -> document that resolution only dismisses the blocker; it does not guarantee script success.
- [Users may expect `resolve-blocker` to handle every Unity dialog] -> keep help and spec wording explicit about the supported blocker types and actions.

## Current Limits

- Windows only
- `--project-path` only
- Supported blocker types only:
  - `save_modified_scenes_prompt`
  - `save_scene_dialog`
- Supported action only:
  - `cancel`
