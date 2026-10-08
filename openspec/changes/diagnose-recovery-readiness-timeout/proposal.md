## Why

A launch-recovery wait can time out even though the requested project's Editor was
launched and became ready. Observed on the validation host during a real-host run of
`tests.test_real_host_integration` (case
`test_cold_launch_retries_on_transient_failure_against_real_host`, part 1):

```
_warm_up_project_exec -> exit 10, status "running"  (after the full 240s wait budget)
session: owner=published_endpoint_recovery
         base_url=http://127.0.0.1:55234
         unity_pid=87640
diagnostics.recent_editor_log_lines:
  "[UnityPuerExec] Port 55233 unavailable: ..."
  "[UnityPuerExec] Published endpoint at .../Temp/UnityPuerExec/endpoint.json"
  "[UnityPuerExec] Ready on port 55234"
diagnostics.last_health_error: "no endpoint matched the target project yet"
diagnostics.idle_seconds: 20.126
```

The Editor itself is healthy: it published its endpoint and logged `Ready on port 55234`.
The CLI's recovery wait reported `running` for the entire budget and never claimed that
endpoint. This is the counterpart of `diagnose-exec-endpoint-misroute`: the endpoint scan
was fixed for *initial* discovery, but a recovery wait that already holds a candidate
`base_url` can still fail to match the ready, project-owned endpoint that replaced a stale
publication — and then reports a non-terminal `running` forever rather than resolving it.

This was intermittent rather than constant, so it is a P2 investigation: the environment
(several unrelated Unity Editors on the host, port 55233 already taken) may be a
precondition, and the fix depends on which resolution step actually dropped the endpoint.

## What Changes

- Determine why the recovery wait could not match a ready endpoint whose own log recorded
  `Ready on port <p>`: is the published candidate a stale pre-launch record, is the live
  `/health` identity mismatch (project path / session marker), or does the wait never
  re-run the range scan after the candidate port is reclaimed?
- Decide whether the durable contract needs strengthening or whether the code violates
  the existing "Project-scoped commands validate control endpoint identity" and
  "Recovery-vs-launch decisions are project-scoped" requirements as written.
- Add a regression at the unit layer (mocked health transitions: stale candidate port,
  ready endpoint on a later port) plus a real-host confirmation.
- Widen the CLI's control-port scan bound from 55231–55249 to the service's actual bind
  range 55231–55250 (`MaxPortAttempts = 20`). A mismatch rather than the observed failure,
  but the fallback scan makes full-range coverage load-bearing, and the durable requirement
  already promised "the bounded control-port range that the Unity control service binds
  within". Pinned against the package source by a layout test.
- The durable contract delta: investigation confirmed that the requirement's normative
  text was too weak, because its stated purpose was only "never waits on the preferred
  port" while the observed wait held a stale candidate on the endpoint's own port. The
  delta therefore adds one explicit scenario **and** one normative sentence: a readiness
  site holding a candidate endpoint must treat it as a fast path only and fall back to
  range-scan discovery when it cannot be confirmed. See `design.md` for the confirmed
  root cause and `validation-evidence.md` for the real-host before/after.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `formal-cli-contract`: adds one explicit scenario to "Project-scoped commands validate
  control endpoint identity", naming the observed case — a recovery wait holding a stale
  candidate endpoint must still claim the ready, project-matched endpoint that appears on
  another port in the range, instead of reporting a non-terminal `running` until its
  budget expires.

## Impact

- Affected code: `cli/python/unity_session.py` (the readiness resolvers),
  `cli/python/direct_exec_client.py` (the control-port range bound), and the
  `wait-for-exec` resolution path in `cli/python/unity_puer_exec_runtime.py`.
- Affected behavior: project-scoped recovery readiness resolution after a cold launch
  when the preferred port is unavailable and a candidate endpoint is stale.
- Affected validation: `tests.test_unity_session`, `tests.test_unity_session_cli`,
  `tests.test_unity_session_modules`, `tests.test_package_layout`, and the real-host case
  that surfaced it.
- No change to the launch itself, the log-isolation model, or the port-binding contract.
