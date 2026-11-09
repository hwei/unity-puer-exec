# Proposal

## Why

The repository's default unit-test selection is written down twice and guarded as "the two lists
agree". That guard has a blind spot that no amount of agreement can close: **a module that is
missing from both lists is invisible to a set-equality comparison between them.** Both sides omit
it, so the comparison passes.

Five mocked-layer modules currently sit in that hole — 134 test cases that run in under four
seconds, need no Unity Editor and no validation host, and are executed on no pull request and no
push to `main`:

- `tests.test_fake_user32` (12)
- `tests.test_unity_modal_blockers` (68)
- `tests.test_real_host_retry` (11)
- `tests.test_release_openupm_tool` (30)
- `tests.test_response_file_output` (13)

`git log -S` shows none of these names has ever appeared in either list, so this is a long-standing
omission rather than a recent regression.

It surfaced during `fake-user32-cross-process-divergence` (archived `2026-11-09`). That change
installed four mocked pins and a two-mutant probe for a bug class that had already reached a
release once — and then discovered that its own new pins land in the unselected 134, so nothing
would run them in CI. A pin in a suite nobody runs is not a pin.

The narrow "add five modules" fix would close today's gap and leave the mechanism that produced it
intact: the next new `tests/test_*.py` is equally invisible by default. The fix therefore has two
halves — select what exists, and make the *unselected remainder* an explicit, reviewed decision
rather than an accident of omission.

## What Changes

- The five mocked-layer modules join both the CI workflow's module arguments and the documented
  default-suite command line, taking the default suite from 19 modules to 24 (~134 more cases,
  measured ~3.6 s on this machine).
- The default-suite guard gains a second property that a set comparison cannot express: every
  `tests/test_*.py` on disk SHALL be either selected in both lists or named in an explicit
  exclusion list with a stated reason. A new module that is added to neither list fails the guard
  by name instead of silently not running.
- The exclusion list starts with the single legitimate exclusion,
  `tests.test_real_host_integration` (needs a live Unity Editor and a prepared validation host,
  runs only under its explicit gate). The existing assertion that this module stays out of both
  lists is subsumed by the new property rather than duplicated.
- No product, CLI, package, or payload change. No change to what the real-host layer covers.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `unit-test-github-action`: gains an added requirement that the selected set be complete with
  respect to the test files on disk — every module is selected or explicitly excluded with a
  reason — so that "the two lists agree" and "the lists cover the directory" are both enforced.

## Impact

- **CI**: `.github/workflows/unit-tests.yml` gains five module arguments. Measured cost of the
  five modules in a clean `git archive` checkout with `UNITY_PROJECT_PATH` unset: 134 tests,
  3.6 s. The suite is otherwise unchanged.
- **Docs**: `openspec/specs/validation-host-integration/how-to-run.md` — the documented default
  suite command line gains the same five module arguments, and the test-layer prose gains a note
  that the mocked list must remain complete against `tests/`.
- **Tests**: `tests/test_default_suite_selection.py` gains the on-disk enumeration property and
  the exclusion table; a mutation probe demonstrates the new property fails when a module is
  dropped from both lists.
- **Prerequisite evidence**: the five modules must pass in a checkout with no `.env` and no
  `UNITY_PROJECT_PATH`, because the existing requirement "Default unit tests do not require
  repository-local Unity project configuration" applies to them the moment they are selected. If
  any of them fails that condition, it does not belong in this change; the disposition flips to
  "exclude with a stated reason".
- **Not in scope**: pruning, renaming, or restructuring existing test modules; changing the
  real-host layer; migrating any test out of the mocked layer.
- **Related**: `fake-user32-cross-process-divergence` (archived `2026-11-09`) is the change during
  which the gap was found, and whose four new pins are among the 134 that this change puts under
  CI. `pin-default-suite-module-list` (archived `2026-11-09`) built the two-list comparison this
  change completes.
