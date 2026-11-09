# Proposal

## Why

`test_script_updater_consent_dialog_recovery_against_real_host` failed on the 0.13.0 real-host run with:

```
observed_title='Script Updating Consent', observed_body=''
File a follow-up fingerprint extension.
```

The dialog existed. The body was empty. `_read_dialog_body_text` collects only children whose
window class is exactly `Static`:

```python
if class_name != "Static":
    return True
```

That assumption held while the case was reaching its diagnosed `skipTest` path, so nothing
ever exercised the reader. On Unity 2022.3.62f2 the ScriptUpdater consent dialog did appear —
which is what the case wants — and the reader returned `""`, so the case degraded from a
diagnosed skip into a hard failure.

This is not only a test-harness defect. The same `_read_dialog_body_text` feeds
`_list_windows_dialogs`, and `_match_dialog_spec` matches the ScriptUpdater dialog **by body
text** because its title is unstable across Editor versions. An empty body therefore also
means the product cannot recognize the dialog: it is not auto-declined, and a caller waiting
on a compile sees it reported as `unknown_modal_dialog` (or, if the modal discrimination
rejects it, not reported at all) instead of `warning = "api_updater_declined"`. The real-host
run confirms the consequence — `api_updater_declined` appears zero times in a suite that
includes the consent-dialog case.

The wider point is that the reader's own contract is unstated. It says "Returns `""` when
nothing can be read", which makes an unreadable dialog indistinguishable from a dialog with no
text, and the caller cannot tell a matched-and-declined dialog from an unmatched one it never
saw.

## What Changes

- `_read_dialog_body_text` reads text from every descendant window that carries readable
  text, not only children of class `Static`. The class filter is replaced by a text
  predicate, because the message may live in `SysLink`, `DirectUIHWND`, or a nested container
  depending on the Unity version, and a message the CLI can read is a message it should
  fingerprint.
- The traversal becomes recursive, so text inside a container child is reached. The current
  one-level `EnumChildWindows` only sees direct children; a nested arrangement reads as empty
  for the same reason.
- The reader reports *why* it returned nothing. A distinct outcome separates "the dialog has
  no readable text" from "the enumeration failed", so a future run can name the blocker
  instead of filing another fingerprint extension against an empty string.
- `test_script_updater_consent_dialog_recovery_against_real_host` stops treating an empty body
  as a fingerprint mismatch. An empty body from a dialog whose title matches the ScriptUpdater
  family is reported as a diagnosed skip naming the unreadable-body blocker, matching the
  case's existing contract for "cannot be triggered on this host". A *non-empty* body that
  matches no fingerprint still fails, which is the case the fingerprint-extension message
  exists for.
- Mocked coverage pins the new reader behavior against synthetic window trees (nested
  containers, non-`Static` text carriers, a textless dialog), and a mutation probe confirms
  the tests fail when the `Static` filter or the recursion is removed.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `modal-dialog-surface`: the body-text reader gains a stated contract — read text from any
  readable descendant, traverse recursively, and distinguish "no text" from "enumeration
  failed" — because the ScriptUpdater catalog entry is matched on that text, so an unreadable
  body silently disables auto-decline.

## Impact

- **CLI**: `cli/python/unity_modal_blockers.py` — `_read_dialog_body_text` and whatever
  diagnostic the callers can surface; `_match_dialog_spec` and `dismiss_api_updater_dialog`
  are unchanged in behavior for a successfully-read body.
- **Host**: none. No package change, no protocol change.
- **Tests**: new mocked cases over synthetic window trees; the real-host consent-dialog case
  gains the empty-body skip path.
- **Compatibility**: additive. A dialog that used to read as empty and go unmatched now
  matches and is auto-declined, which is the behavior the catalog entry already intended.
- **Not in scope**: producing the consent dialog deterministically. Whether a given host
  surfaces it at all remains environment-dependent; this change only guarantees that when it
  does surface, the CLI can read it.
