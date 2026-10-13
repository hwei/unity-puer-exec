## 1. Characterize the observed failure

- [ ] 1.1 Extract the full failing transcript and boundary report for `test_play_settles_a_pending_change_then_reaches_playing` from the validation run (`WinError 10054`, exit shape, whether a retry was attempted). Verify: the finding cites the recorded transcript, not memory.
- [ ] 1.2 Read `_post_play_mode` / `_run_play_mode_command` and record which transport conditions retry, the bound, and which conditions return terminal. Verify: the finding names the branch the observed error would have taken.

## 2. Attempt a bounded reproduction

- [ ] 2.1 Run the affected `play` case repeatedly against the validation host and record pass/fail and any boundary reports. Verify: reproduction attempts are bounded and their count is stated.
- [ ] 2.2 If a segment of the run reliably precedes the reset (for example a mid-reload bind), stage that edge deliberately and observe whether `play` retries or returns terminal. Verify: the staged condition is reported, not inferred.
- [ ] 2.3 If it does not reproduce within the bound, record that outcome with the observed timing and the environment, and stop.

## 3. Finding and Closeout

- [ ] 3.1 Record the disposition: reproducible retry-bound gap (with evidence) or environmental flake (with the bounded non-reproduction). Verify: the finding states which, and names the evidence.
- [ ] 3.2 If a gap is confirmed, draft the separate product-change recommendation and its evidence; do not implement the fix here. Verify: no product code changed.
- [ ] 3.3 Run `openspec validate reproduce-play-mode-transport-reset-flake --strict` and `openspec validate --all`. Verify: valid with `skip_specs: true`.
- [ ] 3.4 Complete the required apply closeout review and record the finding with allowed categories.
