# Tasks

## 1. Project-path settle composition

- [ ] 1.1 Compose the project-path settle from the two existing primitives: in
      `_settle_after_automatic_refresh`, keep `_ensure_project_session_ready_after_refresh(args)`
      first so the endpoint is re-resolved across a reload, then call `wait_for_compile_cycle` on
      the returned session's `base_url` with the same appear, settle, and health budgets
      `_settle_base_url_after_refresh` uses. Verify: `python -m unittest tests.test_unity_session_cli`
      passes and the new mocked case from 2.1 passes.
- [ ] 1.2 Treat `COMPILE_OUTCOME_TIMEOUT` from that wait as "still in flight" on the project-path
      branch too, returning `None` so the caller reports the non-terminal refreshing phase exactly
      as it does today. Verify: the mocked case from 2.2 passes.
- [ ] 1.3 Record the compile wait's `api_updater_declines` into the same `recovery` object the
      base-url branch records into, so a decline during a project-path settle is not lost. Verify:
      the mocked case from 2.2 passes and `python -m unittest tests.test_unity_session_cli` passes.

## 2. Mocked coverage

- [ ] 2.1 Add a mocked case asserting the project-path settle calls the compile-wait primitive with
      the appear window (`args.appear_timeout_seconds`, falling back to
      `DEFAULT_COMPILE_APPEAR_TIMEOUT_SECONDS`) and the compile-scale settle budget, and that it
      polls the endpoint the readiness step resolved rather than the pre-settle one. Verify:
      `python -m unittest tests.test_unity_session_cli` passes.
- [ ] 2.2 Add mocked cases for the two outcomes that must not change: an exhausted cycle returns
      the non-terminal refreshing phase, and a settled or `no_compile_observed` cycle proceeds to
      the one permitted resubmit. Verify: `python -m unittest tests.test_unity_session_cli` passes.
- [ ] 2.3 Run the default mocked suite as documented in
      `openspec/specs/validation-host-integration/how-to-run.md`. Verify: every listed module passes
      with no new failure or skip.

## 3. Real-host validation

- [ ] 3.1 Add a real-host case that a compile-triggering file rewritten byte-identically reaches
      `status: "completed"` in a **single** `exec --project-path` invocation, with
      `refresh.triggered: false` on the resolving decision and the probe named in
      `paths_suppressed`. Verify:
      `UNITY_PUER_EXEC_RUN_REAL_HOST_TESTS=1 python -m unittest tests.test_real_host_integration.RefreshOnChangeRealHostTests`
      passes against the host in `.env`.
- [ ] 3.2 Confirm the genuine-change path is unchanged: an ordinary `.cs` edit still compiles, still
      crosses the domain reload, and still reaches `completed` in one project-path invocation.
      Verify: the same command as 3.1 passes, including the pre-existing
      `test_code_change_refreshes_once_then_does_not_refresh_again` and
      `test_identical_content_rewrite_does_not_loop_the_refresh`.
- [ ] 3.3 Record the wall-clock cost of a project-path `exec` whose refresh compiles nothing, before
      and after, so the added appear window is measured rather than assumed. Verify: the two
      transcripts are captured in the closeout summary.

## Workflow follow-up

- Archive the change with `openspec archive settle-project-path-refresh-on-compile-edge` once the
  real-host evidence is recorded and the review requirements are satisfied.
- Verify the archived result: `openspec validate --all` and
  `python -m unittest tests.test_openspec_spec_hygiene`.
