## Context

Observed on the validation host while running the real-host suite on a machine with
several unrelated Unity Editors open. The requested project's Editor was launched by the
CLI, published its endpoint, and logged readiness — but the CLI's recovery wait held a
candidate and never matched the live endpoint:

```
wait-for-exec -> status "running" for the full 240s budget
session.owner = published_endpoint_recovery
session.base_url = http://127.0.0.1:55234
session.unity_pid = 87640
recent_editor_log_lines:
  "[UnityPuerExec] Port 55233 unavailable: ..."
  "[UnityPuerExec] Published endpoint at .../endpoint.json"
  "[UnityPuerExec] Ready on port 55234"
last_health_error = "no endpoint matched the target project yet"
idle_seconds = 20.126
```

The Editor is provably healthy (its own log says so). So the failure is in resolution, not
in the Editor. `diagnose-exec-endpoint-misroute` already hardened *initial* discovery to
range-scan with health-identity matching. The residual case is a wait that has already
picked a candidate `base_url` and must notice when that candidate is stale while a ready,
project-matched endpoint exists elsewhere in the range.

## Goals / Non-Goals

**Goals:**

- Identify the resolution step that failed to claim the ready endpoint and why.
- Make a recovery wait converge on the ready, project-matched endpoint.
- Keep the "never claim another project's endpoint" guarantee and the bounded wait.

**Non-Goals:**

- The automatic-refresh request-recovery defect (that is
  `diagnose-exec-missing-after-auto-refresh`).
- The CLI empty-response parse defect (that is `diagnose-empty-response-parse-error`).
- Changing the launch path, the log-isolation model, or the control-port binding rules.

## Decisions

### Decision 1: Candidate staleness vs. identity mismatch are different failures

The `last_health_error` text ("no endpoint matched the target project yet") can come from
two states that look alike but need different fixes: the candidate is stale (dead pid /
no listener) and the wait never re-scanned, or a listener answers but its identity does
not match the project (project path / session marker) and the wait never moved on. Task
1.2 must separate them with a mocked transition. A stale candidate points at a
re-scan gap; an identity mismatch points at the health-comparison predicate.

### Decision 2: The fix converges, it does not widen

The existing requirement already promises range-scan discovery at "recovery waiting" and
"the wait that follows a cold-start launch". If the code violates that, the fix restores
the promise and the delta is only an explicit scenario. The fix must not introduce a
broader "claim any ready endpoint" behavior — a ready endpoint owned by another project
stays unclaimable (proposal 2.3).

### Decision 3: Bounded wait survives

A wait that can no longer find any recoverable signal must still terminate with its
terminal outcome; convergence must not become an unbounded poll (task 2.4).

## Risks / Trade-offs

**[The defect is only reproducible under multi-instance contention]** → If the stale
candidate only appears when another project holds a port in the range, the unit
reproduction mocks that transition and the real-host confirmation (3.2) reproduces the
contention. That is accepted; a mocked health transition is the honest way to pin a
race that depends on host state.

**[A re-scan on every wait tick could be expensive]** → Range-scan discovery probes a
bounded set of ports. If the fix re-scans per tick, it must keep the preferred-port fast
path and only sweep when the current candidate is not ready; task 2.4's bounded-wait
check covers the cost indirectly, and review covers the fast path.
