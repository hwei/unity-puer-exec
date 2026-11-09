# Tasks

## 1. Promote the inventory walk into the test layer

- [ ] 1.1 Move the AST classification from `.tmp/spike_post_command_window_scans.py` into
      `tests/test_real_host_reset.py` as reusable helpers: staging-command detection, window-read
      detection (including `get-blocker-state`, classified **before** the generic staging branch),
      and per-case grouping in source order. Keep the parsed suite path as a module constant so
      the guard and any future inspection read the same file. Verify:
      `python -m unittest tests.test_real_host_reset` passes.
- [ ] 1.2 Pin the classifier itself against synthetic source snippets: a `get-blocker-state` call
      is recognized as a window read and does **not** count as the staging command that precedes
      it; a staging helper followed by a direct `_list_windows_dialogs` is ordered correctly.
      Verify: the same command, and that removing the window-read-before-staging branch makes a
      named case fail.

## 2. The guard

- [ ] 2.1 Add a guard case that fails when a real-host case both references an auto-recovered
      dialog trigger and performs a window read after a product-stage command. Report offending
      case names and line numbers, never a bare count. Verify:
      `python -m unittest tests.test_real_host_reset` passes against the current suite, and the
      guard names `test_script_updater_consent_dialog_recovery_against_real_host` when the
      previous, race-shaped version of that case is restored on a scratch copy.
- [ ] 2.2 Assert the six sound post-command observations are not flagged, and pin the allowlist
      reason in the message contract: a case staging a save-scene / modified-scene / unknown
      prompt is reported as sound, not as an unexplained exception. Add one assertion that names
      at least one such case, so an over-broad guard cannot pass by flagging nothing.
      Verify: the same command.

## 3. Durable rule

- [ ] 3.1 Confirm the rule the guard enforces is stated where the next real-host author will
      read it — the `validation-host-integration` spec delta lands as the durable statement, and
      the real-host case docstring that motivated the change names it. Verify:
      `python -m unittest tests.test_openspec_spec_hygiene` passes and the delta validates.

## 4. Regression

- [ ] 4.1 Run the default mocked suite as documented in
      `openspec/specs/validation-host-integration/how-to-run.md`. Verify: every listed module
      passes with no new failure or skip.

## Workflow follow-up

- Archive with `openspec archive real-host-window-scan-after-product-recovery` once the guard is
  in the default suite and green.
- Verify the archived result: `openspec validate --all` and
  `python -m unittest tests.test_openspec_spec_hygiene`.
