# Proposal

## Why

The `Unit Tests` workflow runs on `windows-latest` with `actions/setup-python` and no
dependency-install step. `tests/test_package_layout.py:77` is the only test in the repository
that imports a third-party library (`yaml`), and it guards it with
`self.skipTest("PyYAML not installed")`. On a runner with no site-packages that skip fires, so
the assertion that actually parses `release.yml` — and would catch a stamp step whose block scalar
was silently truncated by a column-0 line — never runs on the CI machine it was written for.

The gap is self-concealing in the usual way: a skip is a pass to a green check, so CI reports
success whether the YAML is parseable or not. It surfaced during
`select-every-mocked-test-module` (archived `2026-11-09`), whose 3.12 verification run showed
`OK (skipped=1)` where the 3.9 local run showed `OK`; the difference was PyYAML presence, not the
interpreter version.

There is exactly one such dependency, so this is a small, bounded fix rather than a general
"CI has no environment" problem.

## What Changes

- The `Unit Tests` workflow installs the repository's test dependencies before running the
  suite, so no selected test silently skips for a missing third-party import.
- The dependency set becomes an explicit, tracked artifact rather than an implicit expectation
  that the runner happens to have it.
- `tests/test_package_layout.py` stops treating a missing PyYAML as a benign skip when running
  under CI: the same condition becomes a failure there, so a future regression in provisioning
  cannot hide behind a green check again. A bare local interpreter without PyYAML still skips, so
  a contributor without the dependency is not blocked.
- No change to the selected module list, to product code, or to any test's assertions.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `unit-test-github-action`: gains a requirement that the workflow provision every third-party
  dependency the selected suite imports, and that a dependency-missing skip is not a silent pass
  in the CI environment.

## Impact

- **CI**: `.github/workflows/unit-tests.yml` gains an install step; no change to the module
  arguments or the runner image.
- **New tracked file**: a requirements file naming the test-time dependencies (PyYAML today).
- **Tests**: `tests/test_package_layout.py` — the `ImportError` branch becomes environment-aware.
- **Docs**: `openspec/specs/validation-host-integration/how-to-run.md` notes that the adopted
  local setup for the default suite is `python -m pip install -r <requirements file>`.
- **Not in scope**: pinning Python package versions beyond what the requirements file expresses,
  adding a lock file or a package manager, caching, or changing the release workflow's existing
  `pip install pyinstaller` step.
- **Related**: `select-every-mocked-test-module` (archived `2026-11-09`) is where the skip was
  observed and deliberately left as a follow-up rather than folded into that change's scope.
