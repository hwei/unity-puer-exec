# Proposal

## Why

`tests/fake_user32.py` models `user32` as a scripted, in-process tree of `FakeWindow` objects.
That is the right shape for most of the modal-blocker code: it keeps real `ctypes` buffers and
callbacks while scripting only the API surface. But it has a blind spot that produced a shipped
bug.

The ScriptUpdater consent dialog's body could not be read, and the root cause was not the class
filter the first diagnosis blamed. It was this:

```
Edit   GetWindowTextW -> 'Static'        (length 6)
Edit   WM_GETTEXT     -> 'Some of this projects source files refer to API ...'  (length 272)
```

`GetWindowTextW` **cannot read another process's control text**. For a foreign child control it
returns a cached stub. `SendMessageTimeoutW(WM_GETTEXT)` returns the real text. The fake answered
both calls with the same text, so the mocked layer could not distinguish "the code read the
message" from "the code read a stub". Every mocked test passed while the real product could not
see the dialog at all.

That defect was fixed by adding two fields to `FakeWindow` (`cached_text`, `answer_wm_gettext`)
and a `SendMessageTimeoutW` method. Those fields close the one gap that was found. They do not
express the general hazard, which is:

> An in-process fake answers a call the way the same call behaves *within this process*. Several
> Win32 calls behave differently when the target window belongs to another process. Where the
> product relies on the cross-process behavior, an in-process fake silently answers a question
> the product never asked.

Nothing in the harness marks which calls carry that hazard, so the next one will be found the
same way this one was: by a real-host failure after a release.

## What Changes

- The cross-process divergence class becomes explicit in the fake rather than incidental to two
  fields: a control that is "foreign" answers cross-process-sensitive calls the way a foreign
  control does, and the fake states which calls those are.
- The harness documents that `GetWindowTextW` is valid only same-process or for a top-level
  window caption, and that a body read must use `WM_GETTEXT`.
- A guard pins the shape: the mocked layer must be able to reproduce the measured
  `GetWindowTextW`-stub / `WM_GETTEXT`-message divergence, so a future simplification of the
  fake that collapses them fails the suite instead of quietly removing the coverage.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `validation-host-integration`: the mocked Win32 double gains a stated model of
  cross-process-sensitive calls, and the suite gains a check that the divergence stays
  expressible.

## Impact

- **CLI**: none.
- **Host**: none.
- **Tests**: `tests/fake_user32.py` and its smoke tests in `tests/test_fake_user32.py`; possibly
  a new mocked case asserting the divergence model.
- **Compatibility**: additive for existing tests. A fixture that wants the old
  "everything is readable" behavior must now say so, which is the point.
- **Not in scope**: enumerating every Win32 call with a cross-process behavior difference. The
  change models the ones the product actually uses and leaves a stated place to add the next.
