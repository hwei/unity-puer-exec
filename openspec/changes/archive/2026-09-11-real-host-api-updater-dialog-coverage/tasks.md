## 1. Dialog trigger fixture

- [x] 1.1 Add a host fixture that seeds a source file referencing an obsolete/`[UnityUpgradable]` API so Unity's ScriptUpdater prompts on import, and restores or removes it after the case so the host is left clean
- [x] 1.2 Verify the fixture actually produces the consent dialog on the current validation host and Unity version, or record the precise blocker for a diagnosed skip

## 2. Real-host recovery assertions

- [x] 2.1 Add a real-host case that, with the consent dialog visible, runs a CLI wait/exec and asserts the dialog is auto-declined with the command's primary status preserved and `warning = "api_updater_declined"` attached
- [x] 2.2 Assert the dialog is never surfaced as `modal_blocked` and that source files were not rewritten (declined, not accepted)
- [x] 2.3 Capture the observed dialog message text on a non-English host so a fingerprint extension can be filed as a follow-up if needed

## 3. Coverage closeout

- [x] 3.1 Wire the case into the opt-in real-host suite so it skips cleanly (with a diagnosed reason) when prerequisites are unmet, mirroring the other real-host cases
- [x] 3.2 Run the case against the validation host and capture the evidence needed to close the change, or record it as a validation-gap with the trigger blocker
