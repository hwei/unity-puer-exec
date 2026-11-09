# Tasks

## 1. State the model

- [ ] 1.1 Name the cross-process hazard in `tests/fake_user32.py`: the module docstring states
      that the double answers in-process semantics, and that `GetWindowTextW` is valid only for a
      same-process window or a top-level window caption. Document `title` / `cached_text` /
      `answer_wm_gettext` as one model rather than three independent flags. Verify:
      `python -m unittest tests.test_fake_user32` passes.
- [ ] 1.2 Add a `foreign_control(hwnd, real_text, gwt_stub=...)` fixture helper that constructs
      the measured shape (real text via `WM_GETTEXT`, stub via `GetWindowTextW`) and say so in
      its docstring. Verify: the same command.

## 2. Pin the divergence

- [ ] 2.1 Add mocked cases asserting that a `foreign_control` answers `GetWindowTextW` and
      `GetWindowTextLengthW` with the stub while `SendMessageTimeoutW(WM_GETTEXT)` answers the
      real text, and that `_read_dialog_body` over a tree containing it returns the real text.
      Verify: `python -m unittest tests.test_fake_user32 tests.test_unity_modal_blockers` passes.
- [ ] 2.2 Add a mutation probe: collapsing the two reads in the double (so `GetWindowTextW`
      answers `title`) must make a named test fail, and separately making `WM_GETTEXT` answer the
      stub must make a named test fail. Record the mutant count. Verify: the probe reports every
      mutant caught.

## 3. Use the model where the measured tree is pinned

- [ ] 3.1 Re-express the measured ScriptUpdater tree in
      `tests/test_unity_modal_blockers.py` through `foreign_control` instead of two hand-set
      fields, keeping every existing assertion. Verify:
      `python -m unittest tests.test_unity_modal_blockers` passes and the assertions are
      unchanged in meaning.

## 4. Regression

- [ ] 4.1 Run the default mocked suite as documented in
      `openspec/specs/validation-host-integration/how-to-run.md`. Verify: every listed module
      passes with no new failure or skip.

## Workflow follow-up

- Archive with `openspec archive fake-user32-cross-process-divergence` once the pins are green.
- Verify the archived result: `openspec validate --all` and
  `python -m unittest tests.test_openspec_spec_hygiene`.
