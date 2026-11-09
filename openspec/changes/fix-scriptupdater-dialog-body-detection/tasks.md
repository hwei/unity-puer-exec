# Tasks

## 1. Reader contract

- [ ] 1.1 Replace the `class_name != "Static"` filter in `_read_dialog_body_text` with a
      text-accepting predicate, and make the traversal recursive so text inside a container
      child is reached. Keep the concatenation order deterministic (window-tree order, parent
      before descendants) and keep returning a single string for `_match_dialog_spec`'s `in`
      checks. Verify: `python -m unittest tests.test_unity_modal_blockers tests.test_fake_user32`
      passes.
- [ ] 1.2 Return a distinguishable outcome for "enumeration failed" versus "no readable
      text", and surface it where a caller can name it. Do not change the string returned on
      success, so fingerprint matching is untouched. Verify: the mocked cases from 2.2 and
      2.3 pass.

## 2. Mocked coverage

- [ ] 2.1 Pin the three tree shapes that motivated the change: a message carried by a
      non-`Static` child, a message nested one container deep, and a dialog with no readable
      text at all. Assert the first two produce the fingerprint-matching sentence and the
      third produces the named "no readable text" outcome. Verify:
      `python -m unittest tests.test_unity_modal_blockers` passes.
- [ ] 2.2 Assert the existing behavior is preserved for a plain `Static`-child dialog, so the
      change cannot regress the shape this code was written for. Verify: the same command.
- [ ] 2.3 Add a mutation probe: removing the recursion, and separately restoring the
      `Static`-only filter, each make a named test fail. Record the mutant count. Verify: the
      probe reports every mutant caught.

## 3. Real-host coverage

- [ ] 3.1 Change `test_script_updater_consent_dialog_recovery_against_real_host` so an empty
      body from a title matching the ScriptUpdater family becomes a diagnosed skip naming the
      unreadable-body blocker, while a non-empty non-matching body still fails with the
      fingerprint-extension message. Verify: `python -m unittest tests.test_real_host_reset`
      passes (the classification is pure-Python and needs no Editor).
- [ ] 3.2 Re-run the case against the 2.2.2 validation host and record which of the three
      outcomes it takes: auto-declined with `warning = "api_updater_declined"`, a diagnosed
      skip naming the trigger blocker, or a diagnosed skip naming the unreadable body. Verify:
      `UNITY_PUER_EXEC_RUN_REAL_HOST_TESTS=1 python -m unittest
      tests.test_real_host_integration.RealHostIntegrationTests.test_script_updater_consent_dialog_recovery_against_real_host`.

## 4. Regression

- [ ] 4.1 Run the default mocked suite as documented in
      `openspec/specs/validation-host-integration/how-to-run.md`. Verify: every listed module
      passes with no new failure or skip.

## Workflow follow-up

- Archive the change with `openspec archive fix-scriptupdater-dialog-body-detection` once the
  real-host outcome is recorded and the review requirements are satisfied.
- Verify the archived result: `openspec validate --all` and
  `python -m unittest tests.test_openspec_spec_hygiene`.
