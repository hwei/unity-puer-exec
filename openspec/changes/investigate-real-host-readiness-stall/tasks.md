## 1. Baseline And Reproduction

- [ ] 1.1 Capture a focused reproducer for the `ensure-stopped -> fresh UnityLockfile -> wait-until-ready -> unity_stalled` sequence and preserve the key diagnostics in the change notes or validation transcript.
- [ ] 1.2 Identify which current `tests.test_real_host_integration` failures are stale assertions versus genuine readiness instability, and record the split before changing code.

## 2. Harness And Runtime Corrections

- [ ] 2.1 Update the real-host test helpers and assertions to match the current CLI surface, including the current exec observation checkpoint and current exec failure payloads.
- [ ] 2.2 Harden the real-host teardown/startup boundary so sequential cases do not enter a false recovery path after an incomplete stop.
- [ ] 2.3 If harness hardening alone is insufficient, tighten project-scoped readiness recovery so fresh lock evidence without a recoverable editor does not degrade into an unexplained stall.
- [ ] 2.4 Preserve or expose enough diagnostics on the relevant stall path to distinguish incomplete stop, stale session state, and true blocked-editor cases.

## 3. Real-Host Validation And Closeout

- [ ] 3.1 Run targeted real-host validations for the reproduced teardown/recovery sequence and the updated observation-checkpoint path.
- [ ] 3.2 Run the full `python -m unittest tests.test_real_host_integration` suite and confirm whether any remaining failures are outside this change's scope.
- [ ] 3.3 Update the upstream `add-exec-script-args` closeout state and recommend archive readiness only after this change restores a trustworthy real-host gate.
