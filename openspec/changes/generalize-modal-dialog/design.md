## Context

See proposal.md for motivation (asymmetric cost of unknown modal dialogs blocking
the Editor main thread, and silent data-loss risk of default-cancel on save-scene).

The current blocker layer (`cli/python/unity_modal_blockers.py`) already enumerates
every visible titled window owned by the Editor pid via `_list_windows_dialogs`
(`:322`) and reads child `Static` text. The drop happens at `_match_dialog_spec`
(`:298`): anything that does not match `WINDOWS_DIALOG_SPECS` (title-keyed) or
`WINDOWS_BODY_DIALOG_SPECS` (message-body-keyed) is silently discarded, so `exec` /
`wait-for-exec` hang until a human clicks.

`resolve-blocker` today (`unity_puer_exec_surface.py:67-69`,
`unity_puer_exec_runtime.py:1862`) accepts only `--action cancel` and operates only
on supported types. `formal-cli-contract:473-535` and `validation-host-integration:118-133`
currently require `--action cancel` to succeed on the save-scene dialogs.

Upstream findings that remain true:
- `api-updater-recovery` behavior is unchanged; the ScriptUpdater consent dialog must
  stay auto-recovered (`_list_supported_modal_blockers` already excludes it) and never
  be reclassified as unknown or exposed as a blocker.
- `safe_mode_dialog` is auto-dismissed in the exec path (`unity_puer_exec_runtime.py:2166`)
  and SHALL remain on the `SetForegroundWindow` + `keybd_event` keyboard path
  (`formal-cli-contract:839`).
- Behavioral gate stays the trigger: dialogs are inspected only when exec has stalled
  (`timed out` / `running` via `_should_check_exec_blocker`, `unity_puer_exec_runtime.py:2203`),
  not on every request.

The gap this design closes: an allowlist classifier that drops unknowns, plus a default
cancel that can discard unsaved scene work, replaced by a reporting classifier plus an
explicit button-targeted resolution path.

## Goals / Non-Goals

**Goals:**
- Report every true modal dialog owned by the Editor pid, including ones outside the catalog.
- Discriminate true modals from non-blocking Editor windows (Preferences, Project Settings,
  Build Settings, About Unity) using owner/style/size, not mere visibility+title.
- Drop automatic action on unknown dialogs; never click a button on an unrecognized prompt.
- Provide an explicit button-targeted `resolve-blocker` path so a reported dialog is resolvable.
- Keep `safe_mode_dialog` cancelable via `--action cancel`; keep api_updater invisible.

**Non-Goals:**
- Auto-resolving unknown dialogs (always requires an explicit caller decision).
- Changing the ScriptUpdater recovery behavior or making it visible.
- Cross-platform / non-Windows support (stays Windows-only, matching all existing recovery).
- A new catalog entry per dialog class going forward (the point is to stop needing them).

## Decisions

### D1. `resolve-blocker` argument shape — keep `--action cancel` for Safe Mode only, add `--action click`

Resolved per user choice **Method A**.

```
resolve-blocker --project-path X
  --action cancel                              # LEGAL ONLY for safe_mode_dialog
  --action click --hwnd <int> --button "<label>"   # save-scene + unknown dialogs
```

Rationale: once save-scene dialogs leave the supported set, `--action cancel` has exactly
one legal target (Safe Mode), so keeping it preserves the existing contract and the
historical "cancel == Enter Safe Mode" semantics without redefining them. A new
`--action click --hwnd <int> --button "<label>"` covers the unified explicit-decision path
for both known save-scene dialogs and unknown dialogs, satisfying the proposal's "click a
named button" requirement.

Alternatives considered:
- **B (rejected)**: remove `--action cancel` entirely and unify on `click`. Cleaner, but
  breaks `formal-cli-contract:473` ("supported only `--action cancel`") and
  `validation-host-integration:118-133`, and any caller already scripting cancel. A keeps
  existing safe-mode callers working.

Validation: `--hwnd <int>` is taken from the `get-blocker-state` / `exec` `modal_blocked`
payload. Before clicking, the CLI re-checks that the hwnd is still a visible titled window
owned by the requested project's Editor pid; if not, returns `status = "resolution_failed"`,
`error = "window_not_found"` (no action taken). This prevents a stale or foreign hwnd from
driving a click.

### D2. Modal discrimination — dialog class required, then owner state

Two host findings (see `validation-evidence.md`) reshaped this. Owner-disabled is **not**
sufficient, and the size bound is **not** a prompt-size test.

**Dialog class is the decisive signal.** A true modal disables the Editor's whole window tree,
so while a real `Save Scene` dialog was up, a Unity panel *also* saw a disabled owner:

```
hwnd=339396 class=UnityContainerWndClass popup=True size=(335, 581)
    owner=5702300 owner_enabled=False    # disabled by the real modal, not by itself
```

Style plus size matched it, so it was reported as `unknown_modal_dialog` and sorted ahead of the
real dialog. Unity's own windows are `UnityContainerWndClass`; Windows dialogs are `#32770`.
Requiring that class is what separates them, and it holds regardless of owner state.

**Real file dialogs are large.** `Save Scene` measured 1200x720, so the original 900px bound
rejected it. It was reported only because catalog title hits bypass discrimination; as an unknown
it would have been dropped. The bound is now 1600 — a loose sanity bound against the Editor's own
windows, not a prompt-size test.

```
is_modal(w):
    if class_name(w) != "#32770": return False    # Unity windows, panels, main window
    if not (popup_style(w) and sized(w)): return False
    owner = GetWindow(w, GW_OWNER)                # GW_OWNER = 4
    if owner != 0:
        return not IsWindowEnabled(owner)         # owned dialog: blocks iff owner disabled
    return True                                   # ownerless dialog (e.g. Safe Mode)
```

Inspection loop (replaces the allowlist drop at `_match_dialog_spec`):

```
for w in visible_titled_windows(pid):
    spec = _match_dialog_spec(w)
    if spec is None:
        if is_modal(w):
            report unknown_modal_dialog(hwnd, title, body, buttons)
        # else: skip non-blocking Editor window (no longer dropped silently)
    elif spec.type == api_updater_dialog:
        continue                               # never exposed; still auto-declined elsewhere
    else:
        # Catalog title hit reports without discrimination: title is the existing
        # contract, and gating it could stop reporting dialogs reported today.
        report known dialog (save_scene_dialog / save_modified_scenes_prompt / safe_mode_dialog)
```

Fallback policy: when discrimination is uncertain for a window, the window is **downgraded to
non-blocking**, never promoted to a blocker. Prefer a missed harmless window over a false modal
that hangs exec. This is a deliberate asymmetry: false positives cost the caller a hang, false
negatives cost one re-check on the next stall.

### D3. Blocker payload shape — `type` is the sole discriminator, no `known` field

`known` was considered and dropped: `known == (type != "unknown_modal_dialog")` is a pure
function of `type`, so the field carries zero information and only creates a driftable
invariant (`type = "save_scene_dialog"` with `known = false`). Callers check
`type == "unknown_modal_dialog"` as the single signal that CLI-side automatic action is
forbidden and an explicit decision is required.

```jsonc
// Unknown dialog — identified purely by type
{
  "type": "unknown_modal_dialog",
  "hwnd": 12345,
  "title": "...",
  "body": "...",
  "buttons": [{"label": "&Yes", "ctrl_id": 6}, {"label": "&No", "ctrl_id": 7}]
}

// Known dialog — type identifies it; no `known` field
{
  "type": "save_scene_dialog",
  "hwnd": 999,
  "title": "Save Scene",
  "body": "...",
  "buttons": [{"label": "&Save", "ctrl_id": 1}, {"label": "Cancel", "ctrl_id": 2}]
}
```

Save-scene dialogs keep their stable `type` values (`save_scene_dialog`,
`save_modified_scenes_prompt`) so existing payloads and guidance remain readable; only the
automatic policy changes (no default cancel). The `unknown_modal_dialog` payload includes
enough to act on: `title`, `body`, and `buttons[]` (each with `label` and `ctrl_id`).

`default_button` is dropped along with the per-button `is_default` flag (D7 #1): both depend
on an unresolved host mechanism (`WM_GETDEFID` vs default-pushbutton style), and shipping a
best-effort field would invite callers to treat it as authoritative. A caller wanting the
dialog's default action reads the button labels and decides explicitly — which is the point of
the change.

### D4. Button enumeration — `_enumerate_buttons(dialog_hwnd)`

Returns every clickable push-button child control: `{hwnd, label, ctrl_id}`.

Win32 reports checkboxes, radio buttons, and group boxes under the same `Button` window class,
and `EnumChildWindows` recurses into nested containers, so a naive "every `Button` child"
return would surface controls the click chain (D5) can act on but that no caller should be
clicking. Enumeration therefore includes only controls clickable as an action: it excludes
checkbox / radio / group-box styles (`BS_CHECKBOX`, `BS_AUTOCHECKBOX`, `BS_RADIOBUTTON`,
`BS_AUTORADIOBUTTON`, `BS_3STATE`, `BS_AUTO3STATE`, `BS_GROUPBOX`) and excludes controls that
are disabled or invisible. A control that cannot be clicked is not a candidate, because
reporting it would make `buttons[]` a list containing entries a `--button` match can name but
never successfully act on.

`--button "<label>"` matching strips `&` mnemonics and trims, then matches exactly or
case-insensitively. If no button matches the label, `resolve-blocker --action click` returns
`status = "resolution_failed"`, `error = "button_not_found"`.

### D5. Click chain priority — message-level first, focus-stealing last, Safe Mode exempt

```
click(button_hwnd):
  1. BM_CLICK      SendMessage(button_hwnd, BM_CLICK, 0, 0)        # no focus steal
  2. WM_COMMAND    SendMessage(owner, WM_COMMAND, BN_CLICKED<<16 | ctrl_id, button_hwnd)
  3. posted key    PostMessage(button_hwnd, WM_KEYDOWN/VK_RETURN); PostMessage(...WM_KEYUP)
  (Safe Mode exempt: always SetForegroundWindow + keybd_event VK_RETURN, never this chain)
```

`--action cancel` for `safe_mode_dialog` keeps the existing keyboard path untouched
(`_click_via_keyboard`). For unknown and save-scene dialogs, prefer the message-level chain
(1 then 2 then 3) to avoid foreground stealing that can disturb the operator's desktop.
Success is confirmed by the existing disappearance check in `resolve_modal_blocker`.

### D6. Spec deltas required (captured in the `specs` artifact, not here)

- **New capability `modal-dialog-surface`**: detect/report any blocking modal dialog owned
  by the Editor, discriminate true modals from non-blocking windows, expose button detail
  for unknowns, and provide the explicit button-targeted resolution path.
- **`formal-cli-contract`**: `resolve-blocker` gains `--action click --hwnd --button` and
  `cancel` becomes Safe-Mode-only; blocker payloads gain the `unknown_modal_dialog` type plus
  a `buttons` array (no `default_button` — see D3). The "supported only `--action cancel`"
  requirement (`:473-535`) and the api_updater line (`:1234`) are reworded accordingly, and
  the save-scene stable-type scenario (`:109-115`) gains its unknown-dialog counterpart.
- **`validation-host-integration`**: `:118-133` requirement that `resolve-blocker --action
  cancel` succeed on save-scene dialogs is replaced by an explicit-click scenario
  (`--action click --hwnd --button "<Don't Save|Cancel>"`), while `:106-117` observation
  (type label unchanged) is retained.
- **`api-updater-recovery`**: unchanged in behavior; deltas only assert it stays
  auto-recovered and is not reclassified as unknown. Its `:63` sentence "Save-scene dialogs
  keep their existing `modal_blocked` contract" becomes half-true after this change (still
  `modal_blocked`, but no default cancel) and is reworded.
- **`runtime-guidance`**: the `("get-blocker-state", "completed")` and `("exec",
  "modal_blocked")` guidance entries (`help_surface.py:887-908`, `:1313-1321`) hardcode
  `--action cancel` in their `argv_template`, which after this change routes save-scene and
  unknown-dialog callers into a path legal only for Safe Mode. Guidance must suggest `cancel`
  only for Safe Mode and `click` otherwise, and the new `window_not_found` /
  `button_not_found` statuses need matrix entries (the matrix must cover every documented
  status per `runtime-guidance:54`).
- **`compile-error-surface`**: not a delta. Its `:192-207` requirements describe
  `list_supported_modal_blockers` reporting `safe_mode_dialog` and exec normalizing it to
  `unity_compile_error`; that behavior is unchanged here, recorded so it is not re-litigated
  at archive time.

## Risks / Trade-offs

- **[Owner-disabled false positives]** → Mitigation: D2 downgrade-to-non-blocking fallback;
  never promote a misclassified window to blocker. Still verifiable only on a real host
  (spike H1 below).
- **[Safe Mode ignores message-level chain]** → Mitigation: Safe Mode is explicitly exempt
  (D5) and stays on the historical keyboard path; the spike only confirms the new chain is
  not *required* for it.
- **[Stale / foreign hwnd]** → Mitigation: D1 re-validates hwnd ownership against the
  project's Editor pid before clicking; `window_not_found` on mismatch.
- **[Backward-incompatibility for save-scene cancel callers]** → Mitigation: Method A keeps
  `cancel` for Safe Mode; save-scene callers must move to `click`. `validation-host-integration`
  is updated to demonstrate the new path (D6).
- **[Button label mismatch across Unity localizations]** → Mitigation: `&` strip + trim +
  case-insensitive match (D4); `button_not_found` on no match.

### D7. Decisions fixed while writing the specs

Not new design branches — these are the undetermined edges in D1-D5 resolved so the specs can
be written as testable SHALLs. Each keeps the change minimal and preserves existing payload
semantics wherever the choice was free.

| # | Question | Decision | Why |
|---|----------|----------|-----|
| 1 | H3 `default_button` derivation | Field dropped, along with per-button `is_default` | Both depend on an unresolved host mechanism; a best-effort field invites callers to trust it |
| 2 | D2: does a catalog title hit still need modal discrimination? | No — a title hit alone reports the known type | Title is the existing contract; adding discrimination could stop reporting dialogs reported today |
| 3 | Multi-blocker ordering | `unknown_modal_dialog` sorts ahead of known types | The unknown one is the likelier true stall; known save-scene types are reachable on their own path |
| 4 | `--action click --hwnd` vs `multiple_supported_blockers` | Click bypasses the multiple-blocker rule | The hwnd is an explicit target; refusing because other dialogs exist breaks the unified path exactly when several are up |
| 5 | Safe Mode detected only by main-window title (no hwnd) | Unchanged: `cancel` returns `no_supported_blocker`; payload omits `hwnd` rather than nulling it | Title fallback means the dialog is already gone; there is nothing to click |
| 6 | Rename `no_supported_blocker`? | Keep the string | Renaming breaks `help_surface.py:303`, `runtime-guidance:44-47`, and existing assertions; semantics widen to "no resolvable blocker" |
| 7 | Unknown-dialog `scope` and exit code | `scope = "exec"`, `EXIT_MODAL_BLOCKED` (19) | Same blocking condition as known dialogs; callers branch on `status`, not on type |

## Test strategy

The new code adds user32 call sites today's tests cannot reach: `GetWindow(GW_OWNER)`,
`IsWindowEnabled`, window style and rect reads, button enumeration with style filtering, and
the D5 click chain. `tests/test_unity_modal_blockers.py` only patches `sys.platform` and injects
fake list/click functions, so none of the discrimination logic is covered;
`tests/test_real_host_integration.py` covers it only on a machine with Unity.

Decision: build a fake-user32 harness for the unit suite — a ctypes-shaped double returning
scripted window trees, owner/enabled/style state, and per-button class names and styles, so
D2's downgrade branch, D4's exclusion rules, and `button_not_found` are covered
deterministically. The default GitHub Actions runner is already `windows-latest`
(`.github/workflows/unit-tests.yml:11`), so the harness runs in CI rather than only on a
validation host. Real-host validation stays responsible for H1/H2 — whether the heuristics hold
against Unity's actual dialogs — which no fake can answer.

## Open Questions (host spikes, deferrable without changing the approach)

These are genuinely host-dependent and are answered by real-host validation, not by design
revision. They do NOT change the specs, the chosen approach, or the task breakdown.

- **H1** *(answered on the host, 2026-09-18)*: real Unity modals do disable their owner, but the
  signal is not unique to them and the size bound was wrong. Both findings are folded into D2 and
  recorded in `validation-evidence.md`. No open question remains.
- **H2** *(answered on the host, 2026-09-18)*: the Safe Mode dialog **does** respond to
  `BM_CLICK` — level 1 of the chain closed it. The D5 exemption is therefore sufficient but not
  necessary; it is kept because the keyboard path has prior host evidence and removing it would
  change a working path for no observed gain. Note `owner=null` for this dialog (it appears before
  the main window exists), so D2's owner test does not apply to it. See
  `validation-evidence.md`.

H3 (`default_button` derivation) is closed: the field is dropped per D3/D7 rather than resolved.
