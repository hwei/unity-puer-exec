# Real-host validation evidence — recovery-readiness timeout

Host: `c3-client-tree2/Project`, Unity 2022.3.62f2.
Wiring: `Project/Packages/manifest.json` pins
`com.txcombo.unity-puer-exec` to `file:../../../unity-puer-exec/packages/com.txcombo.unity-puer-exec`
(no embedded-package shadow).
Probe: `.tmp/real-host-stale-publication-ab.py`.
Logs: `.tmp/real-host-stale-publication-before.log`, `.tmp/real-host-stale-publication-after.log`.

## Staging: multi-instance contention was real, not simulated

Ports in the bounded control range were already held by unrelated Editors when the run
started — the same shape the original failure was observed under:

```
port  status      pid      project_path
55231 ready       89932    F:\C3\c3-client-tree3\Project
55232 ready       91056    F:\C3\c3-client-tree5\Project
```

`tree2` was not running (`project_lockfile_held: False`) but still carried a **residue**
publication naming a dead pid — the state the pre-launch boundary records as
`endpoint_publication_exists: True, project_lockfile_held: False`. With 55231 and 55232
taken, the launched Editor rolled over and bound **55233**.

## Method

The recorded failure was a publication the CLI could not confirm while the project's own
Editor was live. So rather than waiting for that race to recur on its own, the probe stages
it deterministically and holds it still: it copies tree2's real `endpoint.json` and replaces
only `session_marker` with a value the live service cannot have, leaving `port`,
`unity_pid`, and `project_path` truthful. That is exactly what a republish that did not
land leaves behind.

The tamper is confirmed still in place both immediately after the measured exec and after
the resolution step, so the staging provably held for the whole measurement (see
`tamper held through the measurement` / `tamper held after the resolution step` in both
logs). The original publication is restored in a `finally`.

## Result — identical staging, resolver reverted vs. fixed

| | pre-fix (`_make_published_endpoint_resolver` pinned only) | post-fix |
|---|---|---|
| `exec --project-path` exit code | **10** | **0** |
| `status` | **`running`** | **`completed`** |
| `session.owner` | `published_endpoint_recovery` | — (terminal response carries no session block) |
| `session.base_url` | `http://127.0.0.1:55233` | — |
| `session.unity_pid` | `61088` (the live Editor) | — |
| `diagnostics.last_health_error` | **`no endpoint matched the target project yet`** | `None` |
| recorded failure recurred | **yes** | **no** |

The pre-fix row reproduces the original real-host failure field for field: non-terminal
`running`, `owner=published_endpoint_recovery`, `base_url` equal to the **live** port, the
**live** `unity_pid`, and the same `last_health_error` text. Post-fix, under the same held
staging, the exec completes — which it can only do by resolving and routing to a live,
project-matched endpoint.

This satisfies task 3.2's verification: the previously observed `no endpoint matched the
target project yet` `running` timeout does not recur under the same staging.

## Scope of this evidence

- Confirms the CLI-side defect and its fix. It does **not** claim to identify why the
  Editor's republish did not land on the host; the fix is deliberately independent of that,
  because ownership is re-established from `project_path` identity either way.
- The CLI's scan range was widened in this same change, from 55231–55249 to 55231–55250, so
  it covers the range the control service binds (`MaxPortAttempts = 20`). The staging above
  bound 55233 and does not exercise the widened bound; that is covered by
  `test_cli_control_port_range_covers_every_port_the_service_can_bind` and
  `test_discover_project_endpoint_reaches_the_last_port_the_service_binds` at the unit layer.
