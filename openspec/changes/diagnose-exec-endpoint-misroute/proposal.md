## Why

Real-host validation for `improve-large-response-retrieval` observed `exec --project-path <requested-project>` complete successfully while the requested project's Unity Editor was not running at all — the request was instead served by a different, unrelated project's Editor that happened to already be listening on the control-service preferred port (55231). The accepted response's `session_marker` matched the unrelated project's `/health` session_marker exactly, and the CLI persisted a `Temp/UnityPuerExec/session.json` under the requested project recording the wrong project's `base_url`/`unity_pid`/`session_marker`, despite `/health` on that port clearly reporting a different `project_path`. This is a symptom of a possible identity-validation gap in project-scoped endpoint discovery — a durable contract this repository already documents (`project-control-endpoint` spec, and the "Project-scoped commands validate control endpoint identity" requirement in `formal-cli-contract`). Only the symptom was observed once; the root cause in `unity_session.py` has not been read or diagnosed.

## What Changes

- Investigate `unity_session.py`'s project-scoped discovery and health-identity-matching path (`ensure_session_ready` and related range-scan/claim logic) to determine why a live endpoint belonging to a different project was accepted as though it belonged to the requested project.
- Separately assess whether `get-log-source`'s observed default-log-path/preferred-port fallback (returned when no session artifact yet exists for the requested project) is the documented fallback behavior in the log-source-resolution contract, or a related symptom of the same gap — disentangle before concluding scope.
- Once root cause is understood, fix the identity-validation gap so a project-scoped command never claims or persists a session for an endpoint whose live health identity does not match the requested project.
- Add regression coverage (unit tests with mocked health responses simulating "a different project is already ready on the preferred port") so this class of misroute cannot silently regress.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `formal-cli-contract`: adds one explicit scenario to the existing "Project-scoped commands validate control endpoint identity" requirement, naming the exact observed case (preferred port occupied by a different, already-ready project while the requested project has no local session artifact and is not yet running). This does not change the requirement's normative text — the general "on any port" language already covers this case — it makes the case explicit and testable. The observed symptom looks like a code-level violation of the existing contract rather than a genuine spec gap; if investigation instead finds the durable requirement text itself needs different substantive changes, this delta will be revised before tasks are finalized.

## Impact

- **Python CLI:** `cli/python/unity_session.py` (project-scoped discovery, health-identity validation, session artifact persistence); `cli/python/unity_session_logs.py` if the default-log-path fallback needs adjustment.
- **Tests:** new unit coverage for the misroute scenario; existing `tests/test_unity_session*.py` suites are the likely home.
- **Origin:** discovered during `improve-large-response-retrieval`'s real-host validation; see `openspec/changes/improve-large-response-retrieval/results/validation-evidence.md` for the original observed symptom and reproduction context. That change made no code changes for this issue and is unaffected by it.
