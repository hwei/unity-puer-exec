## Why

Project-scoped `exec --project-path` only ever probes and waits on the single preferred control port (`55231`) plus whatever endpoint a prior session artifact recorded. When the target Editor lives on a non-preferred port in the `[55231, 55250)` range — because another project already owns `55231`, or because a freshly launched Editor rolled over — the CLI cannot see it. The result, observed in real agent usage, is that `--project-path` appears to "not launch" or to silently fail: it actually launches or detects a running Unity PID, then waits on the wrong port until it times out. The same missing primitive forces agents to hand-scan `/health` across the range to figure out which port belongs to which project.

## What Changes

- Make project-scoped control-endpoint discovery **range-aware**: instead of probing only the preferred `base_url`, scan the bounded control-port range and claim the candidate whose `/health.project_path` matches the requested project.
- Apply range-aware discovery at **every** readiness site in `ensure_session_ready`, not just one: the initial discovery probe, the post-launch-claim re-probe, the recovery wait, and the cold-start post-launch wait. Today all four are pinned to the single preferred port, so even a clean CLI-driven cold start fails when the launched Editor rolls over off `55231`.
- Strengthen the identity guarantee: because every candidate endpoint is identity-matched before use, a non-preferred-port Editor for another project can never be silently connected to ("静默连错"), and an Editor for the target project on a non-preferred port is correctly claimed.
- Keep base-url selector mode unchanged: `--base-url` continues to target the caller-supplied endpoint directly with no range scan and no project validation.
- **Enabled but deferred (out of scope here):** a `list-sessions` diagnostic command that prints `port → project_path → pid` for the range. Once the internal scan exists it is a thin surface over the same primitive; this change does not ship it, but records it as a follow-up so the discovery work is not duplicated later.

## Capabilities

### New Capabilities
<!-- None. The behavior belongs to an existing contract requirement and is strengthened in place. -->

### Modified Capabilities
- `formal-cli-contract`: strengthen **"Project-scoped commands validate control endpoint identity"** to require an active bounded control-port range discovery scan with project-identity matching, covering (a) a live target Editor on a non-preferred port with no session artifact, (b) recovery that waits on the actually-bound port rather than the preferred port, and (c) cold-start launches whose Editor rolls over off the preferred port.

## Impact

- **Code:** `cli/python/unity_session.py` — `ensure_session_ready` and its helpers (`_probe_health` call sites, `_build_recovery_session`, the cold-start launch wait, `wait_ready_with_activity`). The single `base_url` thread becomes a range-aware candidate selection that resolves to the matched endpoint.
- **Shared contract:** the CLI must scan the same bounded range the Unity control service binds within (`project-control-endpoint`'s port-selection requirement). No server-side requirement changes; the CLI consumes the existing `/health` identity fields (`project_path`, `port`, `base_url`, `unity_pid`, `session_marker`).
- **Behavior:** `--project-path` becomes reliable when the preferred port is occupied by another project; the dominant manual workaround (hand-launch + `--base-url` + manual `/health` confirmation) is no longer required for the common multi-instance case.
- **Tests:** real-host regression coverage for the non-preferred-port and cold-start-rollover paths (evidence target: host-validation).
- **No breaking changes:** base-url mode and the single-instance preferred-port path are unaffected.
