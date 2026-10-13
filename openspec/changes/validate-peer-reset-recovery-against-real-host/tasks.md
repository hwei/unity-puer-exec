## 1. Run the real-host suite

- [ ] 1.1 Confirm the real-host prerequisites are actually present before claiming anything: `UNITY_PROJECT_PATH` resolves, the host is prepared, `prepare_validation_host.py` reports `"embedded_package_shadowing": false`, and the Editor is resolvable. Verify: each prerequisite is stated with its observed value; a missing one means the run skips and that is recorded as a skip.
- [ ] 1.2 Run the real-host suite and record the full result. Verify: the transcript names the play-mode cases explicitly, including `test_play_settles_a_pending_change_then_reaches_playing` — the case that originally produced the `10054`. Not just an aggregate pass count.
- [ ] 1.3 Confirm the play path reaches `playing` without an opaque `status: "failed"` / exit 1. Verify: the assertion is on the observed exit code and payload status of that specific case, not on the suite exit code alone.

## 2. Confirm the broadened catch does not mask a live condition

- [ ] 2.1 Check whether any real-host case now reports `not_available` that previously reported a specific, more actionable state. This is the concrete risk of catching `OSError` broadly, and it is only observable live. Verify: each `not_available` in the run is attributed to a cause; an unattributed one is a finding, not a pass.
- [ ] 2.2 If a real transport reset occurs during the run, confirm the payload names it as `not_available`, exits 12, and still carries the reset detail. Verify: the actual emitted payload is quoted, including the errno text. If no reset occurred, record that plainly — do not claim confirmation.

## 3. Closeout

- [ ] 3.1 Set `evidence: host-validation` on this change's `meta.yaml` and `updated_at`. If the run skipped or no reset occurred, record the weaker evidence value actually obtained instead.
- [ ] 3.2 Run `openspec validate validate-peer-reset-recovery-against-real-host --strict` and `openspec validate --all`.
- [ ] 3.3 Complete the apply closeout review, stating explicitly whether the fix is now confirmed against a live endpoint or only against a simulated one. Do not let a green unit suite and a green real-host run be reported as the same kind of confirmation.