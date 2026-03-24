## 1. Lifecycle Contract

- [x] 1.1 Extend the pending exec artifact schema and helper APIs to persist explicit lifecycle metadata, including schema version plus creation and update timestamps.
- [x] 1.2 Define the bounded retention policy and centralized cleanup rules for recoverable, terminal, expired, and malformed pending artifacts in the runtime helper layer.
- [x] 1.3 Update the OpenSpec deltas and any nearby CLI help or inline comments needed so the public `missing` behavior and bounded local retention policy stay aligned.

## 2. CLI Implementation

- [x] 2.1 Refactor `cli/python/unity_session_logs.py` pending-artifact helpers to validate schema, detect expiry, and opportunistically sweep stale siblings in the project pending directory.
- [x] 2.2 Refactor project-scoped `exec` and `wait-for-exec` flows in `cli/python/unity_puer_exec_runtime.py` to use centralized lifecycle helpers for artifact creation, refresh, and terminal cleanup.
- [x] 2.3 Ensure expired or malformed pending artifacts are deleted and surfaced to callers as non-recoverable `missing` outcomes instead of remaining as reusable local state.

## 3. Verification

- [x] 3.1 Extend repository unit coverage for fresh artifact creation, timestamp refresh, terminal deletion, expiry handling, malformed-artifact cleanup, and stale-sibling sweeping.
- [x] 3.2 Run the targeted real-host validation path against `UNITY_PROJECT_PATH` to confirm the accepted `exec -> running -> wait-for-exec` lifecycle still succeeds after hardening.
- [x] 3.3 Capture the validation result in the change record so later archive review can distinguish product regressions from host-environment noise.
