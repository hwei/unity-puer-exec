## Why

Modal dialog recovery is catalog-driven: `unity_modal_blockers._match_dialog_spec` matches a visible window against `WINDOWS_DIALOG_SPECS` (title-keyed) and `WINDOWS_BODY_DIALOG_SPECS` (message-body-keyed), and anything unmatched is discarded. Because a modal dialog blocks the Editor main thread, the consequences are asymmetric — the enumeration already exists and is not the problem, but a dialog outside the catalog produces neither a blocker report nor any way for the caller to unblock, so `exec` / `wait-for-exec` hang until a human clicks. Every new dialog class has to be hand-added before the CLI can even see it.

Two separate problems compound this:

1. **Unknown dialogs are invisible.** `_list_windows_dialogs` (`:322`) already enumerates every visible, titled window owned by the Editor pid and even reads its `Static` child text. The allowlist is what drops the rest.
2. **Save-scene dialogs are auto-cancellable by default.** `resolve-blocker --action cancel` is defined for them, so a caller that reaches for the obvious unblock command silently discards unsaved scene changes. When an agent modifies a scene and then forgets to save, losing that work should require an explicit, named decision — not be the default action of a generic command.

## What Changes

Decision made, pending host validation:

- **Report unknown modal dialogs instead of dropping them.** Turn the allowlist into a classifier: catalog dialogs keep their stable type labels, everything else is reported as `blocker.type = "unknown_modal_dialog"` with enough detail to act on (`title`, `body`, `buttons[]`). Type alone distinguishes the two; there is no separate `known` field. Automatic action on an unknown dialog is never taken — clicking a button on an unrecognized prompt risks data loss on dialogs like delete or overwrite.
- **Modal discrimination is required.** "Visible window with a title" is too weak on its own: `Preferences`, `Project Settings`, `Build Settings`, and `About Unity` are all separate visible titled windows that do not block exec. The primary discriminator is owner state — a true modal disables its owner (`GetWindow(GW_OWNER)` then `IsWindowEnabled`). Style and size checks cover dialogs without an owner. The existing behavioral gate stays as the trigger: dialogs are inspected when exec has stalled (`timed out` / `running`), not on every request.
- **Save-scene dialogs move to the general unknown path.** `save_modified_scenes_prompt` and `save_scene_dialog` keep their stable `type` values so existing payloads and guidance remain readable, but they leave the supported set: `resolve-blocker` no longer offers a default cancel for them. Type labels stay; only the automatic policy changes.
- **`resolve-blocker` must be able to click a named button.** Reporting without an unblock path is a dead end. The command currently accepts only `--action cancel` and operates only on supported types; it needs to target a specific hwnd and button label.
- **Foreground-free click chain where it works.** Existing click paths are `BM_CLICK` (no focus steal, already used for save-scene and API Updater), `SetForegroundWindow` + `keybd_event` (Safe Mode), and the superseded `mouse_event` path. For dialogs that respond to messages, prefer `BM_CLICK`, then `WM_COMMAND`, then posted `WM_KEYDOWN`/`WM_KEYUP` over the focus-stealing path. Safe Mode is exempt: it stays on the existing keyboard path regardless of outcome, because it is rare and because it was moved off `BM_CLICK` historically for ignoring it.

## Open Before Implementation

The `resolve-blocker` argument shape is settled (design D1). Two host-dependent questions remain and are answered by real-host validation rather than design revision; neither changes the specs or the task breakdown:

- Whether Safe Mode's dialog responds to `WM_COMMAND` or posted key messages at all. It was moved off `BM_CLICK` for ignoring standard messages, so the message-level chain may not reach it.
- Whether owner-disabled detection holds for Unity's real dialogs, and what the false-positive rate is against `Preferences` / `Project Settings` / `Build Settings`.

## Capabilities

### New Capabilities

- `modal-dialog-surface`: detect and report any blocking modal dialog belonging to the Editor process, discriminate true modals from non-blocking Editor windows, expose button detail for unknown dialogs, and provide an explicit button-targeted resolution path.

### Modified Capabilities

- `formal-cli-contract`: `resolve-blocker` gains `--action click --hwnd --button` and `cancel` becomes Safe-Mode-only; blocker payloads gain the `unknown_modal_dialog` type and a `buttons` array.
- `validation-host-integration`: real-host coverage for unknown-dialog reporting and for the save-scene dialogs' non-automatic disposition.
- `api-updater-recovery`: unchanged in behavior, but its dialog must remain auto-recovered rather than reclassified as unknown.

## Impact

- `cli/python/unity_modal_blockers.py` — classification, modal discrimination, button enumeration, click chain.
- `cli/python/unity_puer_exec_runtime.py` — blocker normalization and payload construction.
- `cli/python/help_surface.py` — guidance for unknown-dialog status and the new resolution path.
- `tests/test_unity_modal_blockers.py`, `tests/test_real_host_integration.py` — existing save-scene assertions change meaning: type labels remain, automatic cancel does not.
- `openspec/specs/formal-cli-contract/spec.md` (`:113-114`), `openspec/specs/validation-host-integration/spec.md` (`:114`, `:124`, `:131`) — save-scene requirements describe supported-blocker resolution today.
- Windows-only, matching all existing modal recovery.
