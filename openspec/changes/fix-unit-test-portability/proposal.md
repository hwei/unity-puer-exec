## Why

The latest `Unit Tests` GitHub Actions run failed on the hosted Windows runner even though the same suite passed locally. The failures came from portability assumptions in validation-host manifest rewriting and from a unit test that still required a real `UNITY_PROJECT_PATH`.

## What Changes

- Make validation-host manifest dependency generation tolerate Windows cross-volume paths instead of crashing on `os.path.relpath(...)`.
- Keep the normal validation-host wiring path reproducible when the repo and host are on the same volume, but define a deterministic fallback when they are not.
- Remove the real-environment dependency from the default `tests.test_unity_session` unit suite so the GitHub-hosted unit-test workflow stays self-contained.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `validation-host-integration`: clarify how local package dependency rewriting behaves when the repository and validation host live on different Windows volumes.
- `unit-test-github-action`: require the default unit-test suite to remain independent from repository-local `UNITY_PROJECT_PATH` configuration.

## Impact

- Affected code: `tools/prepare_validation_host.py`, `tests/test_prepare_validation_host_tool.py`, `tests/test_unity_session.py`
- Affected systems: validation-host helper tooling, default GitHub Actions unit-test workflow on Windows runners
