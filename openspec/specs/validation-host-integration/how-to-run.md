# Running Tests

## Test Layers

This repository has two distinct test layers:

**Mocked tests** (default):
```
python -m unittest discover -s tests -p "test_*.py"
```
Cover parsing, payload contracts, status codes, and local helper logic. Run without any external dependencies.

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

## Current Coverage Chain

The real-host regression exercises this primary chain:

```
wait-until-ready -> exec --include-log-offset -> wait-for-result-marker -> wait-for-log-pattern --extract-json-group
```

For the full set of runtime validation requirements this covers, see [spec.md](spec.md).
