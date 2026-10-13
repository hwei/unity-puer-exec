## 1. Fix the transport boundary

- [ ] 1.1 Widen the handlers in `direct_exec_client.invoke_command` so a connection reset is caught and mapped to the `not_available` payload instead of escaping. Verify: the archived reproduction `repro_play_transport_reset.py`, re-run from its archived location, now reports `RemoteDisconnected` as retryable rather than `ESCAPED`.
- [ ] 1.2 Preserve the underlying reset text (the `10054` errno) in the reported payload while normalizing the status to `not_available`. Verify: the errno text is present in the emitted payload.
- [ ] 1.3 Check the sibling conditions the widened catch admits (`BadStatusLine`, `ConnectionRefusedError`, `ConnectionAbortedError`) and confirm each maps sensibly rather than assuming. Verify: each sibling is either covered by a test or explicitly excluded with a stated reason.

## 2. Confirm the play path recovers

- [ ] 2.1 Confirm `_is_play_mode_transport_drop` now classifies the reset body as retryable so `_post_play_mode` enters its retry branch. Verify: the assertion names the branch the previous failure could not reach.
- [ ] 2.2 Confirm the existing bound still produces the structured not-available exit code when the endpoint never recovers, and that a reset does not make a hard outage worse than before. Verify: the bound used is stated.
- [ ] 2.3 Re-run the default suite and confirm no existing exit-code expectation regresses.

## 3. Closeout

- [ ] 3.1 Add regression coverage for the boundary classification.
- [ ] 3.2 Run `openspec validate recover-peer-reset-transport-drop --strict` and `openspec validate --all`.
- [ ] 3.3 Complete the apply closeout review.
- [ ] 3.4 Note in the closeout whether `classify-peer-reset-on-all-transport-callers` is still needed, since this change fixes the boundary those callers share.