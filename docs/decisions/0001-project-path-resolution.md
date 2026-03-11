# 0001 Project Path Resolution

- Date: 2026-03-11
- Status: accepted

## Decision

Unity project path resolution follows this order:

1. explicit `--project-path`
2. `UNITY_PROJECT_PATH` from the process environment
3. `UNITY_PROJECT_PATH` loaded from repository-local `.env`
4. current working directory

## Rationale

- `unity-puer-exec` is not the validation host repository.
- Repository-scoped `Project/` assumptions would couple productized code back to the host workspace layout.
- Explicit caller input should always win over repository-local defaults.

## Consequences

- `.env` remains a local convenience, not the canonical source of truth.
- Tests that need a real Unity project path should either read the resolved environment or document their requirements close to the test code.
