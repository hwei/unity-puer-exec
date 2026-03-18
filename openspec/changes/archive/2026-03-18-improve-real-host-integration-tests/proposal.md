## Why

Recent work proved several CLI workflows against the real Unity validation host, but that coverage still lives mostly as manual evidence and ad hoc command transcripts. The repository now has strong mocked contract tests, yet it still lacks a repeatable real-host regression path for the CLI flows most likely to break at the Unity/process/log boundary.

## What Changes

- define a queued validation change that turns the current manual real-host checks into a repeatable repository-owned regression workflow
- add a focused real-host integration suite for the critical CLI chain: readiness, `exec --include-log-offset`, and result-marker/log-pattern observation
- keep the suite scoped to the external validation host and local package injection model rather than treating the host repo as product source
- document how contributors prepare the host, run the real-host regression path, and interpret failures separately from mocked unit and contract tests

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `validation-host-integration`: require a repeatable runtime validation workflow that exercises the critical real Unity CLI paths, not only host wiring proof

## Impact

- `tests/` real-host validation entry points and supporting fixtures
- `tools/prepare_validation_host.py` or adjacent repository-owned validation helpers
- validation workflow guidance in OpenSpec artifacts
- local validation against `UNITY_PROJECT_PATH` and the external Unity host project
