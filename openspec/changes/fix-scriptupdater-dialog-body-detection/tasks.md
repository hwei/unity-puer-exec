# Tasks

## 1. Reader contract

- [x] 1.1 Replace the `class_name != "Static"` filter in `_read_dialog_body_text` with a
      text-accepting predicate, and make the traversal recursive so text inside a container
      child is reached. Keep the concatenation order deterministic (window-tree order, parent
      before descendants) and keep returning a single string for `_match_dialog_spec`'s `in`
      checks. Verify: `python -m unittest tests.test_unity_modal_blockers tests.test_fake_user32`
      passes.
- [x] 1.2 Return a distinguishable outcome for "enumeration failed" versus "no readable
      text", and surface it where a caller can name it. Do not change the string returned on
      success, so fingerprint matching is untouched. Verify: the mocked cases from 2.2 and
      2.3 pass.
- [x] 1.3 Read descendant text with `SendMessageTimeoutW(WM_GETTEXT)` rather than
      `GetWindowTextW`, keeping the latter as a fallback. Added after the first real-host
      re-run proved the original diagnosis incomplete: `GetWindowTextW` returns a cached stub
      for a foreign child, so the `Edit` message control read as `'Static'`. Verify: the
      Edit-shaped pins in `DialogBodyReaderTests` and the `get_window_text_only` mutant.

## 2. Mocked coverage

- [x] 2.1 Pin the three tree shapes that motivated the change: a message carried by a
      non-`Static` child, a message nested one container deep, and a dialog with no readable
      text at all. Assert the first two produce the fingerprint-matching sentence and the
      third produces the named "no readable text" outcome. Verify:
      `python -m unittest tests.test_unity_modal_blockers` passes.
- [x] 2.2 Assert the existing behavior is preserved for a plain `Static`-child dialog, so the
      change cannot regress the shape this code was written for. Verify: the same command.
- [x] 2.3 Add a mutation probe: removing the recursion, and separately restoring the
      `Static`-only filter, each make a named test fail. Record the mutant count. Verify: the
      probe reports every mutant caught.
      Probe: `.tmp/scriptupdater_body_guard_teeth.py` — 3 of 3 mutants caught (static-only
      filter, one-level walk, `GetWindowTextW`-only), each by the pins that name it.

## 3. Real-host coverage

- [x] 3.1 Change `test_script_updater_consent_dialog_recovery_against_real_host` so an empty
      body from a title matching the ScriptUpdater family becomes a diagnosed skip naming the
      unreadable-body blocker, while a non-empty non-matching body still fails with the
      fingerprint-extension message. Verify: `python -m unittest tests.test_real_host_reset`
      passes (the classification is pure-Python and needs no Editor).
      Pins: `ScriptUpdaterObservationClassificationTests` (7 cases).
- [x] 3.2 Re-run the case against the 2.2.2 validation host and record which of the three
      outcomes it takes: auto-declined with `warning = "api_updater_declined"`, a diagnosed
      skip naming the trigger blocker, or a diagnosed skip naming the unreadable body. Verify:
      `UNITY_PUER_EXEC_RUN_REAL_HOST_TESTS=1 python -m unittest
      tests.test_real_host_integration.RealHostIntegrationTests.test_script_updater_consent_dialog_recovery_against_real_host`.
      *Outcome recorded: auto-declined with `warning = "api_updater_declined"`.* Measured
      directly from the exec payload by `.tmp/probe_decline_evidence.py`: `exec status=completed`,
      `warning=api_updater_declined`, `warning_detail` present, and the consent dialog sampled
      live mid-run with `body_outcome=read`, `body` matching the fingerprint, and a catalog
      match, then gone after exec. A window scan after the command cannot see this dialog: the
      product declined it before the scan ran, which is why the case now asserts the warning.
      The source fixture was left unrewritten (declined, not accepted).
      Confirmed: the case itself reports `... ok` (`Ran 1 test ... OK`, no skip) against the
      2022.3.62f2 host.

## 4. Regression

- [x] 4.1 Run the default mocked suite as documented in
      `openspec/specs/validation-host-integration/how-to-run.md`. Verify: every listed module
      passes with no new failure or skip.
      Result: `Ran 895 tests in 111.657s` — `OK`, exit 0 (logged to `.tmp/default_suite_run.log`).
      The `unity-puer-session: error: argument command: invalid choice: 'ensure-ready'` line in
      the log is stderr from an unrelated case and was present before this change; it does not
      fail the suite.

## Workflow follow-up

- Archive the change with `openspec archive fix-scriptupdater-dialog-body-detection` once the
  real-host outcome is recorded and the review requirements are satisfied.
- Verify the archived result: `openspec validate --all` and
  `python -m unittest tests.test_openspec_spec_hygiene`.
