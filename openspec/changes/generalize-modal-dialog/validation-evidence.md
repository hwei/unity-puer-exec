# Real-host validation evidence

Host: `c3-client-tree2/Project`, Unity 2022.3.62f2, zh-CN Editor.
Wiring: `tools/prepare_validation_host.py` reported `embedded_package_shadowing: false`
after the embedded v0.9.0 copy was moved out of `Packages/` (renaming to `.bak` is not
enough — Unity still resolves it as `source: Embedded`).

## Tests run

| Test | Result |
|---|---|
| `test_get_blocker_state_reports_save_scene_dialog_against_real_host` | PASS |
| `test_resolve_blocker_cancels_save_scene_dialog_against_real_host` | PASS |
| `test_wait_for_exec_reports_modified_scene_modal_blocker_against_real_host` | PASS |
| `test_resolve_blocker_cancel_is_rejected_for_save_scene_against_real_host` | PASS |
| `test_unknown_modal_dialog_is_reported_against_real_host` | PASS |
| `test_non_blocking_editor_windows_are_not_blockers_against_real_host` | PASS |

## Observed dialogs

Real `Save Scene` (class `#32770`, popup, owner disabled):

```
hwnd=38207646 title='Save Scene' size=(1200, 720)
buttons=[('保存(&S)', 1), ('取消', 2)]
```

Unknown dialog triggered with `EditorUtility.DisplayDialog('Codex Validation Prompt', ...)`,
which has no catalog entry:

```json
{"type": "unknown_modal_dialog", "hwnd": 3802342, "title": "Codex Validation Prompt",
 "body": "", "buttons": [{"label": "&OK", "ctrl_id": 1}, {"label": "&Cancel", "ctrl_id": 2}],
 "scope": "exec"}
```

Resolved by `--action click --hwnd 3802342 --button "&Cancel"`; follow-up
`get-blocker-state` reported `no_blocker`.

## H1 — modal discrimination on real dialogs

Two findings that changed the implementation.

**1. A real Unity file dialog is 1200x720, not prompt-sized.** The design's
`_is_small(w)` test rejected it. `Save Scene` was reported only because catalog title
hits bypass discrimination; as an unknown it would have been dropped. The size bound was
raised to 1600 and is now a loose sanity bound, not a prompt-size test.

**2. Owner-disabled is not unique to the modal.** While the real `Save Scene` dialog was
up, this window also had a disabled owner:

```
hwnd=339396 title='掉落拖尾对照' class=UnityContainerWndClass
    owner=5702300 owner_enabled=False popup=True size=(335, 581)
    children=[('UnityGUIViewWndClass', 'C32.Asset.ItemDropTrailPreviewWindow')]
```

A true modal disables the Editor's whole window tree, so every popup-styled Editor window
sees a disabled owner too. Style plus size matched it (335x581 is prompt-sized). Before the
fix it was reported as `unknown_modal_dialog` and sorted ahead of the real dialog, so
`detect_modal_blocker` returned the wrong blocker.

Fix: discrimination now requires window class `#32770`. Unity's own windows are
`UnityContainerWndClass` and are excluded regardless of style, size, or owner state. Unit
regressions added: `test_unity_window_is_not_a_modal_even_when_owner_is_disabled`,
`test_large_file_dialog_is_still_a_modal`, `test_unity_window_does_not_outrank_a_real_dialog`.

## H2 — Safe Mode

Answered by a probe run, not by a committed test. An earlier note claimed this could not be
exercised without disturbing the host; that was wrong — the suite already has
`test_compile_error_safe_mode_is_transparent_against_real_host`, which writes a broken C# file,
triggers, and deletes it in a `finally`.

A running Editor only *reports* compile failure. The Safe Mode dialog appears when Unity
**starts** with compile errors, so the probe stopped the Editor, wrote the broken script, then
relaunched. Observed:

```
hwnd=11666778 title='Enter Safe Mode?' class=#32770 size=(421, 241) owner=null
buttons=[("&Enter Safe Mode", 1), ("&Ignore", 3), ("&Quit", 2)]
```

**The dialog responds to `BM_CLICK`.** Level 1 of the click chain closed it; levels 2 and 3 were
never reached. So the Safe Mode exemption in D5 is *sufficient but not necessary*: the
message-level chain would work for Safe Mode too.

Two facts worth recording:

- `owner=null` — the dialog appears before Unity's main window exists, so the owner-disabled
  signal in D2 does not apply to it at all. It is classified only by dialog class and size.
- The first button is `&Enter Safe Mode` (ctrl_id 1). The D5 keyboard path sends Enter, which
  activates the default button — same semantics, but the click chain names the button explicitly.

D5 keeps the exemption. Removing it would change a path that currently works, for no observed
gain, and the keyboard path is the one with prior host evidence.

### Host cleanup note

The probe left the target Editor in Safe Mode (`Project - SAFE MODE - ...`) and a stale pid in
the session state made `ensure-stopped` report `not_stopped` (its `taskkill` targeted a pid that
no longer existed). The Editor was stopped by pid directly. Several unrelated Unity Editors for
other projects were running on the machine throughout and were left untouched.

## Localization

The host Editor is zh-CN: save-scene buttons are `保存(&S)` / `取消`, not
`Save` / `Cancel`. Real-host tests now read the label from the blocker payload via
`_pick_cancel_button_label` instead of hardcoding English labels.
