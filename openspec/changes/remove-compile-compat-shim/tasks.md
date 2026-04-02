## 1. Remove Compile Compat Runtime Residue

- [ ] 1.1 Delete `packages/com.txcombo.unity-puer-exec/Editor/UnityPuerExecCompileCompat.cs` and its `.meta` file without changing the formal `UnityPuerExecServer` refresh path.
- [ ] 1.2 Update `tests/test_package_layout.py` so package-layout expectations no longer require compile-compat symbols or file presence.

## 2. Reconfirm Formal Refresh Behavior

- [ ] 2.1 Verify the CLI/runtime code and any related help text still describe `exec --refresh-before-exec` as the authoritative project refresh workflow.
- [ ] 2.2 Run targeted repository tests for package layout and CLI refresh behavior, then record the outcome for closeout.

## 3. Closeout

- [ ] 3.1 Summarize whether any repository-owned compile-trigger compatibility residue remains after removal.
- [ ] 3.2 Produce the required apply closeout finding summary, including whether new follow-up candidates were identified.
