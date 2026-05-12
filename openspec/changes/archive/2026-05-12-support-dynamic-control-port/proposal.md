## Why

Multiple Unity Editors that load `com.txcombo.unity-puer-exec` currently contend for the fixed loopback port `55231`. This makes concurrent project work unreliable: a later Editor can fail to start its listener, or the CLI can route project-scoped commands to the wrong Editor.

## What Changes

- Add dynamic loopback port selection for the Unity-side control service, starting from the existing preferred port and trying later ports when the preferred port is unavailable.
- Extend the Unity health response with endpoint identity fields, including the selected port, base URL, Unity process id, project path, and session marker.
- Treat project-local session artifacts as candidate routing hints until the CLI validates the advertised endpoint against live health identity.
- Persist the selected endpoint and project identity in the project-local session artifact after readiness is confirmed.
- Ensure stale or copied session artifacts do not become authoritative during Unity cold start or after another Editor has taken the recorded port.
- Preserve explicit `--base-url` as the direct-service escape hatch for callers that already know the target endpoint.

## Capabilities

### New Capabilities

- `project-control-endpoint`: Defines the Unity-side project control endpoint, dynamic port selection, health identity, and project-local endpoint artifact contract.

### Modified Capabilities

- `formal-cli-contract`: Project-scoped CLI commands must discover and validate the project control endpoint instead of assuming the fixed default port.

## Impact

- Unity package Editor server: `packages/com.txcombo.unity-puer-exec/Editor/UnityPuerExecServer.cs` and protocol response helpers.
- Python CLI session management: `cli/python/unity_session.py`, `cli/python/unity_session_logs.py`, `cli/python/unity_session_wait.py`, and related tests.
- CLI default/direct transport behavior: `cli/python/direct_exec_client.py` remains usable for explicit direct targets, but project-scoped routing no longer relies on a globally fixed default endpoint.
- Validation and tests: unit tests for stale artifact handling, endpoint identity validation, dynamic port selection, and cold-start readiness; real-host validation should exercise at least one non-default selected port path.
