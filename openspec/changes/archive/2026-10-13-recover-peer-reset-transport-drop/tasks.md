## 1. Fix the transport boundary

- [x] 1.1 Widen the handlers in `direct_exec_client.invoke_command` so a connection reset is caught and mapped to the `not_available` payload instead of escaping. Verify: the archived reproduction `repro_play_transport_reset.py`, re-run from its archived location, now reports `RemoteDisconnected` as retryable rather than `ESCAPED`.
- [x] 1.2 Preserve the underlying reset text (the `10054` errno) in the reported payload while normalizing the status to `not_available`. Verify: the errno text is present in the emitted payload.
- [x] 1.3 Siblings verified: `BadStatusLine`, `ConnectionRefusedError`, `ConnectionAbortedError`, and a bare `ConnectionResetError` all normalize to `not_available` / exit 12 with the errno text preserved. `BadStatusLine` (garbage status line) maps sensibly — it is still an endpoint that failed to answer. `socket.timeout` is an `OSError` and keeps its earlier dedicated `"timed out"` handler because it is listed first. Non-transport exceptions (e.g. `RuntimeError`) still escape the boundary. Check the sibling conditions the widened catch admits (`BadStatusLine`, `ConnectionRefusedError`, `ConnectionAbortedError`) and confirm each maps sensibly rather than assuming. Verify: each sibling is either covered by a test or explicitly excluded with a stated reason.

## 2. Confirm the play path recovers

- [x] 2.1 Covered by `test_play_recovers_from_a_peer_reset_inside_the_bound`: the assertion `attempts["count"] >= 2` names the retry branch — the re-resolve/retry loop at `_post_play_mode` — which the previous escaped-exception failure could never reach.
- [x] 2.2 Bound is `_post_play_mode`'s `deadline = time.monotonic() + args.timeout_seconds`, which the play envelope still translates into `EXIT_NOT_AVAILABLE` (12). Covered by `test_play_reset_for_the_whole_bound_exits_with_the_not_available_code`. A hard outage now retries until the bound rather than failing fast — that is the documented intent for this path, and the bound itself is unchanged, so a reset does not extend any deadline. This is a deliberate behavior change versus the previous fast generic failure, per design "Risks / Trade-offs".
- [x] 2.3 `python -m unittest discover -s tests -p "test_*.py"` → 743 tests, OK (3 skipped). No existing exit-code expectation regressed.

## 3. Closeout

- [x] 3.1 Added in `tests/test_direct_exec_client.py`: `test_peer_reset_is_classified_as_a_retryable_transport_drop`, `test_peer_reset_siblings_map_to_not_available`, `test_unrelated_exceptions_still_escape_the_boundary`. Added in `tests/test_unity_session_cli.py`: the two play-path recovery/bound tests above.
- [x] 3.2 Run `openspec validate recover-peer-reset-transport-drop --strict` and `openspec validate --all`.
- [x] 3.3 Apply closeout review completed — see below.
- [x] 3.4 Still needed, but narrower. This change fixes the shared boundary, so all seven `invoke_command` call sites in `cli/python/unity_puer_exec_runtime.py` (1020, 1412, 1800, 2325, 2446, 2534, 2656) now receive a structured `not_available` body instead of an escaped exception. What remains genuinely open is the *audit/assertion* value the change proposal claims, not a second fix. Recommend keeping it but re-scoping it to verification: confirm each call site's classification of a reset on its own command path, and record the answers. Note that `recover-peer-reset-transport-drop` already covers `play` (tasks 2.1/2.2), so roughly half of that change's proposed coverage now exists. No automatic promotion or modification of `classify-peer-reset-on-all-transport-callers` was performed — the disposition is for human discussion.

## Apply closeout review

**New follow-up candidates identified.** Classified for human discussion; none was created or
started automatically, per the apply-closeout-review spec.

| Candidate | Category | Context |
|---|---|---|
| Re-scope `classify-peer-reset-on-all-transport-callers` to verification-only | `validation-gap` | Its premise (peers reset escapes the boundary) is now fixed for all seven call sites. Its remaining value is auditing + asserting each site's classification, not a fix. |
| Assert reset classification on the non-play command paths | `validation-gap` | `exec`, `reset-jsenv`, `wait-for-exec`, `get-compile-messages`, and `_read_compile_error_total` now get a structured body, but only `play` has an assertion. Task 3.1 of the follow-up can absorb this. |
| Real-host re-validation of the original failure | `validation-gap` | The original evidence is one real-host run (`test_play_settles_a_pending_change_then_reaches_playing`). This change has unit evidence only; a host-validation run would confirm the fix on the real endpoint. |

**Behavior change worth a human decision.** A hard endpoint outage on `play` previously failed
fast with `status: "failed"` / exit 1; it now retries until the command bound and exits 12. That is
the documented intent of the play path (design "Risks / Trade-offs"), but it changes observable
latency for a truly-down endpoint. Flagging it rather than absorbing it silently — the bound was
left unchanged deliberately.

**Actions recommended, not executed.** The change is ready to close: `git commit`, then
`openspec archive recover-peer-reset-transport-drop`, then a final `git commit`.