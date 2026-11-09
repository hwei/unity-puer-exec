# Design

## What "foreign" means in a single-process fake

The double holds every `FakeWindow` in one Python process. Win32 does not know that; it decides
how to answer a text read from the handle's owning process and thread. So the fake needs a
per-window statement of how a foreign reader would be answered, separate from the window's real
text.

Two fields already exist from the fix that motivated this change:

```python
class FakeWindow:
    title = "the window's real text"
    cached_text = None      # what GetWindowTextW answers, when a stub is wanted
    answer_wm_gettext = True  # whether WM_GETTEXT is answered at all
```

They are the right primitives. What this change adds is the naming and the contract: a window
that models a foreign control sets `cached_text` to the stub it would receive, and that is the
one fact a test reader needs.

## Naming

Rather than add another flag, define what the fields mean in one place:

- `title` — the window's real text, as `WM_GETTEXT` returns it.
- `cached_text` — the text `GetWindowTextW` returns, which for a foreign child control is a
  Win32-maintained stub. `None` means "this window is readable the same way both ways".
- `answer_wm_gettext` — `False` models a control that ignores the message.

A helper makes the intent explicit at the fixture:

```python
foreign_control(hwnd, real_text, gwt_stub="Static")
```

which is a `FakeWindow` with `title=real_text`, `cached_text=gwt_stub`. Tests that reproduce the
measured ScriptUpdater tree should read as "this is a foreign control", not as "here are two
strings".

## Why a helper and not a stricter fake

Making every child control foreign by default would break the six-plus existing fixtures that
rely on `GetWindowTextW` answering, and would make the double lie in the opposite direction: a
`FakeWindow` is not foreign, it is a model of a window whose ownership the test chooses. An
explicit constructor states that choice where it is made.

## The pin

`tests/test_fake_user32.py` already has a smoke case asserting the harness faithfully exposes the
calls the blocker code makes. Extend that section:

- a `foreign_control` answers `GetWindowTextW`/`GetWindowTextLengthW` with the stub;
- `SendMessageTimeoutW(WM_GETTEXT)` on the same handle answers the real text;
- `_read_dialog_body` over a tree containing it returns the real text, not the stub.

The third assertion is the one that fails if the double is collapsed, because the product would
then read the stub and the fingerprint would miss.

## Alternatives rejected

- **Keep the two ad-hoc fields and just document them.** Documentation does not fail a build. The
  measured failure was a passing mocked suite over a broken product; only an executable check
  changes that.
- **Model process ownership generally (a `pid` per window and a "current process" on the
  double).** More faithful, but the product never asks for the owner pid when reading text, so
  the extra state would not be exercised by any real code path. It would be a model of Win32, not
  of the product's use of Win32.
- **Delete the `GetWindowTextW` path from production.** It is the correct fallback for a
  same-process window and for a control that ignores `WM_GETTEXT`.

## Risks

- **The helper invites over-use.** A test that marks a control foreign when it does not need to
  is only slightly less faithful than one that does not. Accepted: the helper names a real
  property of the measured tree, and the alternative is the current silence.
- **Coverage is one call family.** `WM_GETTEXT` is the call family this change models. Others
  (`GetWindowTextLengthW` caching, `WM_GETTEXTLENGTH`) are covered only insofar as the stub model
  makes them consistent. A future divergence gets a new field, and the docstring says where.
