# Tasks

## 1. Retain the resolving block

- [ ] 1.0 Add one merge helper used by both exec and play: given the stored dispatch block (or
      `None`) and the resolving response's block, return the dispatch block with every existing
      field kept, `paths_suppressed` set to the ordered, de-duplicated union of both lists, and the
      resolving block attached verbatim under `resolving`. With no dispatch block it returns the
      resolving block unchanged. Use it in the exec refresh loop so the value passed to
      `_inject_refresh_block_into_stdout` is the merged block. Verify: the mocked cases from 2.0
      pass.

- [ ] 1.1 In `_play_pre_settle`, retain the refresh block from a resolving poll as well as from a
      dispatching one, so the block the settle ended on is the block the play result carries. Keep
      the existing retention for the dispatching polls so a play that never resolves still discloses
      what it dispatched. Verify: the mocked cases from 2.1 pass.
- [ ] 1.2 Keep the disclosure additive: `_play_success_result` and `_play_refreshing_payload` still
      attach the block under the same `refresh` key with every field it carries today, so no caller
      changes. Verify: `python -m unittest tests.test_unity_session_cli` passes, including the
      existing `run_play` cases.
- [ ] 1.3 Preserve the no-refresh case: a pre-settle that found nothing pending and whose resolving
      decision suppressed nothing still attaches no `refresh` key. A resolving decision that carries
      a non-empty `paths_suppressed` is retained even when this invocation never dispatched, so a
      suppression on the first poll is disclosed. Verify: the mocked cases from 2.2 pass.

## 2. Mocked coverage

- [ ] 2.0 Add mocked exec cases in `tests/test_unity_session_cli.py`: a dispatch-then-suppress
      exec returns `refresh.triggered: true`, the suppressed path in `refresh.paths_suppressed`, and
      `refresh.resolving.triggered: false`; an exec that never dispatched returns the server's block
      unchanged (no `resolving` key). Verify: `python -m unittest tests.test_unity_session_cli` passes.

- [ ] 2.1 Add a mocked case in `tests/test_unity_session_cli.py` driving `run_play` through a
      dispatch-then-suppress settle — a first `/refresh` answer that triggered, and a later one that
      reported `triggered: false` with a populated `paths_suppressed` — and asserting the play
      success payload's `refresh` names those suppressed paths. Verify:
      `python -m unittest tests.test_unity_session_cli` passes.
- [ ] 2.2 Add mocked cases for the two disclosures that must not change -- a settle that never
      dispatched and suppressed nothing attaches no `refresh` key, and a settle that dispatched and
      resolved on a genuine compile still discloses the refresh that ran -- plus one for the new
      edge: a first poll that resolves with `triggered: false` and a non-empty `paths_suppressed`
      attaches a `refresh` key naming those paths. Verify:
      `python -m unittest tests.test_unity_session_cli` passes.
- [ ] 2.3 Run the default mocked suite as documented in
      `openspec/specs/validation-host-integration/how-to-run.md`. Verify: every listed module passes
      with no new failure or skip.

## 3. Real-host validation

- [ ] 3.1 Add a real-host case that a `play` following a byte-identical rewrite of a compile-triggering
      probe reaches `play_state: "playing"` and names the probe in the play result's
      `paths_suppressed`, reusing the identical-rewrite helper the refresh cases already have.
      Verify:
      `UNITY_PUER_EXEC_RUN_REAL_HOST_TESTS=1 python -m unittest tests.test_real_host_integration.PlayModeCompileBlockRealHostTests`
      passes against the host in `.env`.
- [ ] 3.2 Confirm the neighbouring play cases are unaffected, in particular the one that aborts on a
      failing pre-settle build and the one that settles a genuine pending change before playing.
      Verify: the same command as 3.1 passes with no new failure.

- [ ] 3.3 Update `test_identical_rewrite_completes_in_one_project_path_invocation` (added by
      `settle-project-path-refresh-on-compile-edge`) to the merged shape: the resolving decision is
      `refresh.resolving` with `triggered: false`, and the probe is in `refresh.paths_suppressed`.
      Verify: the same real-host command as 3.1, with `RefreshOnChangeRealHostTests`.

## Workflow follow-up

- Archive the change with `openspec archive disclose-resolving-refresh-block-on-play` once the
  real-host evidence is recorded and the review requirements are satisfied.
- Verify the archived result: `openspec validate --all` and
  `python -m unittest tests.test_openspec_spec_hygiene`.
