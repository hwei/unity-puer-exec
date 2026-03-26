## Context

The repository already uses GitHub Actions for tagged release publishing, but normal development changes do not get automatic mocked-test verification. The test tree currently mixes three different signals:

- pure mocked CLI/runtime tests that run with no Unity dependency
- local helper-tool tests for preparing or cleaning the external validation host
- real-host integration tests that require Unity Editor plus a prepared external project

The real-host boundary is already documented in `openspec/specs/validation-host-integration/how-to-run.md`, but the default automated path does not yet encode that separation. The current helper test filenames also read like integration coverage even though they only exercise local Python tool logic.

## Goals / Non-Goals

**Goals:**
- Add a repository-owned GitHub Actions workflow that automatically verifies the mocked/unit Python test suite on normal development events.
- Make the automated test set explicit so CI never depends on `test_real_host_integration.py` silently skipping.
- Rename the two validation-host helper test modules so their names communicate that they are tool-logic tests, not Unity Editor integration.
- Keep the CI path aligned with the repository's existing Windows-oriented CLI packaging workflow.

**Non-Goals:**
- Add real Unity Editor automation to GitHub-hosted runners.
- Replace the separate real-host validation workflow documented under `validation-host-integration`.
- Introduce a broad test framework migration away from `unittest`.

## Decisions

### Use a dedicated unit-test workflow on GitHub Actions

The repository will add a workflow dedicated to mocked/unit tests rather than extending `release.yml`. This keeps release publishing isolated from routine validation and lets pull requests fail quickly on Python contract regressions.

Alternative considered:
- Reuse `release.yml` for tests. Rejected because tag-only release automation is the wrong trigger surface for ordinary development feedback.

### Run on `windows-latest` with Python 3.12

The workflow will use `windows-latest` and Python 3.12 to match the existing release automation environment closely enough to catch Windows-path and packaging-adjacent issues without introducing a new matrix immediately.

Alternatives considered:
- Linux runners. Rejected for the first pass because the repository already treats Windows as the primary packaging environment.
- A multi-OS matrix. Rejected for now because the immediate gap is missing any automated unit coverage, not broad platform certification.

### Define the CI test set explicitly

The workflow will invoke an explicit mocked/unit test command that excludes `tests/test_real_host_integration.py` by construction instead of by environment-dependent skip behavior. This makes the workflow contract readable and stable even if the real-host test bootstrap logic changes later.

Alternatives considered:
- Run full discovery and rely on real-host tests to skip. Rejected because it blurs test-layer ownership and makes CI behavior dependent on runtime guard code.
- Maintain exclusion logic only in workflow shell script globbing. Rejected because that leaves the repository without a durable, documented command surface for the same unit-test set.

### Rename validation-host helper tests to `*_tool.py`

`test_prepare_validation_host.py` and `test_cleanup_validation_host.py` will be renamed to `test_prepare_validation_host_tool.py` and `test_cleanup_validation_host_tool.py`. The new names communicate that these tests validate repository-owned helper tooling rather than real-host runtime behavior.

Alternative considered:
- Keep current names and rely only on documentation. Rejected because the names continue to suggest Unity-dependent integration when contributors scan the test tree or CI selection list.

## Risks / Trade-offs

- [Explicit unit-test command drifts from the test tree] -> Keep the command repository-owned and document its purpose beside the workflow so future test additions have one obvious place to update.
- [Windows-only CI misses Linux-only issues] -> Accept for the initial workflow; expand to a matrix later if cross-platform Python execution becomes a real requirement.
- [Renamed test files break ad hoc local habits] -> Keep the new names mechanically similar to the old ones and update the documented test command in the same change.
