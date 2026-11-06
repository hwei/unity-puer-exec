# Proposal

## Why

The default unit-test module list is written down **twice** — once as the explicit module
arguments in `.github/workflows/unit-tests.yml`, once as the copy-pasteable command line in
`openspec/specs/validation-host-integration/how-to-run.md` — and nothing in the repository
compares them. They have already drifted: `tests.test_real_host_reset` is in the documented
command line and **absent from CI**, so a mocked-layer test that needs no Unity has not been
running on pull requests or pushes to `main`.

The drift was found by accident, while adding a module to both lists for
`support-puerts-2x-jsenv`. That is the wrong discovery mechanism: a list that is only correct
when someone remembers to edit two files is a list that will be wrong again, and the failure
mode is silent — CI stays green while coverage quietly narrows.

## What Changes

- The immediate defect is fixed: `tests.test_real_host_reset` joins the CI module list, so the
  documented default suite and the executed one are the same set.
- A mocked-layer test derives both lists and asserts they are identical, so a future addition
  to one and not the other fails the default suite rather than narrowing CI silently. The test
  reads the workflow YAML and the documented command line as they are, rather than introducing
  a third representation to keep in sync.
- The `unit-test-github-action` requirement that the selection be explicit is amended to name
  the single-set property, and a new requirement fixes what happens when the two lists
  disagree.
- `tests.test_real_host_reset` is confirmed to belong in the mocked layer before it is added to
  CI: it imports `tests.test_real_host_integration` and drives it under `unittest.mock`, so it
  must not require a Unity Editor or a validation host. If that turns out to be false, the
  disposition flips — the documented list is wrong instead, and the test stays out of CI.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `unit-test-github-action`: "Automated unit-test selection is explicit" gains the requirement
  that the documented default suite and the CI-executed suite are the same set, and a new
  requirement states that a disagreement between them is a failure of the default suite rather
  than a documentation nit.

## Impact

- CI: `.github/workflows/unit-tests.yml` gains one module argument. The suite already runs
  `tests.test_real_host_reset` locally as part of the documented command line, so the expected
  effect on CI runtime is the cost of one more mocked module, not a new test layer.
- Tests: one new mocked-layer test module, or an addition to the existing OpenSpec/tooling test
  module, that parses both lists.
- Docs: `openspec/specs/validation-host-integration/how-to-run.md` is unchanged in content — it
  is already the correct list — but becomes one of the two inputs a test reads, so editing it
  is no longer a docs-only act.
- No product surface changes: no CLI behavior, no Unity package, no payload.
- Related: `support-puerts-2x-jsenv` (archived `2026-11-06`) is the change during which the
  drift was observed. It added `tests.test_puerts_version_compat` to both lists correctly, and
  noticed the pre-existing mismatch while doing so.
