# Running Tests

## Test Layers

This repository has two distinct test layers:

**Mocked and helper-tool unit tests** (default):
```
python -m unittest tests.test_cleanup_validation_host_tool tests.test_direct_exec_client tests.test_openspec_backlog tests.test_openspec_change_meta tests.test_package_layout tests.test_prepare_validation_host_tool tests.test_unity_log_brief tests.test_unity_puer_session tests.test_unity_session tests.test_unity_session_cli tests.test_unity_session_modules
```
Cover parsing, payload contracts, status codes, packaging checks, OpenSpec tooling, and local validation-host helper logic. Run without Unity Editor or a validation-host project.

This is the same default suite executed by the repository's GitHub Actions unit-test workflow for pull requests and pushes to `main`.

**Real-host integration tests** (`tests/test_real_host_integration.py`):
Require a live Unity Editor and a prepared validation host project. Not executed unless explicitly enabled — they skip silently when prerequisites are not met.

## Running Real-Host Regression

Prerequisites:
- `UNITY_PROJECT_PATH` points to the validation host Unity `Project/` directory (set in environment or `.env`)
- Unity Editor is resolvable on this machine
- Validation host has been wired to the local package via `tools/prepare_validation_host.py`

Run command:
```
UNITY_PUER_EXEC_RUN_REAL_HOST_TESTS=1 python -m unittest tests.test_real_host_integration
```

## Result Interpretation

| Result | Meaning |
|--------|---------|
| `skip` | Prerequisites not met (env not set, `UNITY_PROJECT_PATH` missing, Unity Editor not found, or host manifest not wired). Not a product regression. |
| `fail` / `error` | Prerequisites were satisfied but the CLI chain, runtime, log observation, or assertion failed. This is a real-host regression. |

Mocked test passes do **not** substitute for real-host regression. They protect parsing, payload, and local contract logic only.
The default GitHub Actions workflow excludes `tests/test_real_host_integration.py` on purpose; real-host coverage remains a separate manual validation path.

## Current Coverage Chain

The real-host regression exercises this primary chain:

```
wait-until-ready -> exec --include-log-offset -> wait-for-result-marker -> wait-for-log-pattern --extract-json-group
```

For the full set of runtime validation requirements this covers, see [spec.md](spec.md).
