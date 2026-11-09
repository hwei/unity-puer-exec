# Tasks

## 1. State the model

- [x] 1.1 Name the cross-process hazard in `tests/fake_user32.py`: the module docstring states
      that the double answers in-process semantics, and that `GetWindowTextW` is valid only for a
      same-process window or a top-level window caption. Document `title` / `cached_text` /
      `answer_wm_gettext` as one model rather than three independent flags. Verify:
      `python -m unittest tests.test_fake_user32` passes.
- [x] 1.2 Add a `foreign_control(hwnd, real_text, gwt_stub=...)` fixture helper that constructs
      the measured shape (real text via `WM_GETTEXT`, stub via `GetWindowTextW`) and say so in
      its docstring. Verify: the same command.

## 2. Pin the divergence

- [x] 2.1 Add mocked cases asserting that a `foreign_control` answers `GetWindowTextW` and
      `GetWindowTextLengthW` with the stub while `SendMessageTimeoutW(WM_GETTEXT)` answers the
      real text, and that `_read_dialog_body` over a tree containing it returns the real text.
      Verify: `python -m unittest tests.test_fake_user32 tests.test_unity_modal_blockers` passes.
      Pins: `CrossProcessTextReadTests` (4 cases in `tests/test_fake_user32.py`).
- [x] 2.2 Add a mutation probe: collapsing the two reads in the double (so `GetWindowTextW`
      answers `title`) must make a named test fail, and separately making `WM_GETTEXT` answer the
      stub must make a named test fail. Record the mutant count. Verify: the probe reports every
      mutant caught.
      Probe: `.tmp/fake_user32_cross_process_guard_teeth.py` — 2 of 2 mutants caught
      (`get_window_text_collapsed` by `test_foreign_control_answers_get_window_text_with_the_stub`;
      `wm_gettext_stubbed` by `test_foreign_control_answers_wm_gettext_with_the_real_text` and
      `test_body_reader_returns_the_message_not_the_stub`). The failure messages name the
      cross-process read as the thing no longer covered.

## 3. Use the model where the measured tree is pinned

- [x] 3.1 Re-express the measured ScriptUpdater tree in
      `tests/test_unity_modal_blockers.py` through `foreign_control` instead of two hand-set
      fields, keeping every existing assertion. Verify:
      `python -m unittest tests.test_unity_modal_blockers` passes and the assertions are
      unchanged in meaning.
      Result: `test_message_in_an_edit_control_is_read_across_the_process_boundary` and
      `test_edit_message_still_reaches_the_catalog_match` now build the `Edit` with
      `fake_user32.foreign_control(...)`; both keep their original assertions (message present,
      stub absent, catalog match with no blocker listing).

## 4. Regression

- [x] 4.1 Run the default mocked suite as documented in
      `openspec/specs/validation-host-integration/how-to-run.md`. Verify: every listed module
      passes with no new failure or skip.
      Result: `Ran 912 tests in 114.120s` — `OK`, exit 0 (logged to `.tmp/default_suite_run.log`).
      No skips. The only stderr noise is the pre-existing unrelated
      `unity-puer-session: error: argument command: invalid choice: 'ensure-ready'` line.
      Observed separately: neither `tests.test_fake_user32` nor `tests.test_unity_modal_blockers`
      is named in the default-suite module list, so the pins this change adds are not executed by
      that command. Both were run explicitly instead — `python -m unittest tests.test_fake_user32
      tests.test_unity_modal_blockers` → `Ran 80 tests ... OK`. The gap is pre-existing (neither
      module was listed before this change) and is reported as a closeout follow-up rather than
      silently absorbed here.

## Workflow follow-up

- Archive with `openspec archive fake-user32-cross-process-divergence` once the pins are green.
- Verify the archived result: `openspec validate --all` and
  `python -m unittest tests.test_openspec_spec_hygiene`.
