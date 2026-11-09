# Spec Delta

## ADDED Requirements

### Requirement: The Win32 double models cross-process text reads

The mocked `user32` double SHALL be able to reproduce the difference between reading a window's
text with `GetWindowTextW` and with `WM_GETTEXT`. It SHALL allow a fixture to mark a control as
answering `GetWindowTextW` with a cached stub while `WM_GETTEXT` returns the control's real text.

#### Scenario: A fixture reproduces the measured foreign-control stub

- **WHEN a fixture marks a control as returning a cached `GetWindowTextW` value
- **THEN `GetWindowTextW` and `GetWindowTextLengthW` report that cached value
- **AND `WM_GETTEXT` on the same handle reports the control's real text

#### Scenario: A control that ignores the message is expressible

- **WHEN a fixture marks a control as not answering `WM_GETTEXT`
- **THEN the double reports that the message went unanswered
- **AND the production code's fallback path is exercised rather than an empty body being
  produced

### Requirement: The mocked layer pins the cross-process divergence

A mocked test SHALL assert that the divergence above is expressible through the double and that
the product reads the message rather than the stub. The assertion SHALL fail if the double is
simplified to answer both calls identically.

#### Scenario: Collapsing the two reads fails a test

- **WHEN the double is changed so `GetWindowTextW` and `WM_GETTEXT` return the same text for a
  foreign control
- **THEN a named test fails
- **AND its message names the cross-process read as the thing no longer covered

### Requirement: The same-process limitation is stated where fixtures are written

The double's documentation SHALL state which calls it answers with in-process semantics, and
that `GetWindowTextW` is valid only for a same-process window or a top-level window caption.

#### Scenario: A fixture author can see the hazard

- **WHEN a reader opens the fake's module docstring or the model of a text read
- **THEN the cross-process limitation is stated there
- **AND the calls the double answers with in-process semantics are named
