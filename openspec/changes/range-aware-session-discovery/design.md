## Context

`unity_session.ensure_session_ready` is the single funnel every project-scoped `exec` (and project-scoped observation command) passes through to resolve a live, identity-matched control endpoint for the requested project. It already does the right *shape* of work — validate a session artifact, probe live health, compare `/health.project_path` against the target, and launch or recover when nothing valid is found.

The defect is narrower than "discovery is missing": discovery exists, but it is pinned to a **single** endpoint. `base_url` defaults to the preferred port (`direct_exec_client.DEFAULT_BASE_URL` = `http://127.0.0.1:55231`) and is threaded unchanged into every probe and wait site:

```
ensure_session_ready(base_url=55231)
  Phase 1  validate_artifact_endpoint            → artifact url (only non-preferred source today)
  Phase 2  _probe_health(base_url)               → 55231 only        ← target on 55233 invisible
  recovery _build_recovery_session(base_url)      → waits on 55231    ← waits on wrong port → timeout
           + wait_ready_with_activity
  post-claim _probe_health(base_url)             → 55231 only
  cold-start _launch_unity → session(base_url)    → waits on 55231    ← launched Editor may bind 55232+
             + wait_ready_with_activity
```

The Unity control service (`project-control-endpoint` spec) deliberately rolls over to a later port in a bounded range when the preferred port is occupied, so multiple Editors can run concurrently. The CLI never mirrors that rollover on the discovery side. A non-preferred-port endpoint is reachable today **only** via a session artifact, which exists **only** if this CLI previously launched that Editor — so manual launches and cross-project port contention are invisible.

The existing contract requirement `formal-cli-contract` → "Project-scoped commands validate control endpoint identity" already says discovery must not assume a globally fixed default endpoint and must not fall back to the preferred port merely because the selected port differs — but its scenarios only cover the artifact-endpoint cases. It does not mandate an active range scan, which is the concrete mechanism needed to honor the requirement's intent in the no-artifact and rollover cases.

## Goals / Non-Goals

**Goals:**
- Resolve the target project's live control endpoint by an active scan of the bounded control-port range, selecting the candidate whose `/health.project_path` matches the requested project.
- Apply that resolution at every readiness site: initial discovery, post-claim re-probe, recovery wait, and cold-start post-launch wait.
- Preserve strict identity matching so no command is ever routed to another project's Editor, on any port.
- Make `--project-path` reliable when the preferred port is owned by a different project (the dominant multi-instance case from real usage).

**Non-Goals:**
- Shipping a `list-sessions` / discovery command. The internal scan enables it; surfacing it is recorded as follow-up, not built here.
- Changing base-url selector mode. `--base-url` stays a direct, single-endpoint, no-validation path.
- Changing the Unity-side port-selection or `/health` identity contract. This change consumes existing server behavior and identity fields.
- The compile-loop tooling (refresh-before-exec base-url support, wait-for-compile). That is the sibling Proposal B.

## Decisions

### Decision 1: Range scan as the discovery primitive, identity-matched

Introduce a single helper that scans the bounded control-port range (the same range the Unity service binds within), probes `/health` on each candidate, and returns the first ready endpoint whose `project_path` matches the requested project. All discovery/readiness sites call this instead of probing a lone `base_url`.

- **Why over alternatives:**
  - *Broadcast/registry file approach* (each Editor writes a global registry the CLI reads): adds a new cross-process shared-state contract and a new staleness problem; the artifact already taught us live health must be the source of truth (`project-control-endpoint`: "artifact alone is not sufficient proof"). A scan needs no new shared state.
  - *Only fix recovery* (the original framing): insufficient — the cold-start launch wait and the initial probe are pinned to the preferred port too, so a clean CLI-driven launch still fails on rollover. The scan must cover all sites.
- The preferred port remains the **first** candidate, so the common single-instance case keeps its current fast path and cost.

### Decision 2: Identity match is the claim gate on every candidate

A candidate is claimed only when health is `ready`/`ok` **and** `_payload_matches_project(payload, project_path)` holds. This is already the gate in Phase 2; the scan generalizes it across the range. A ready endpoint for a *different* project is skipped, not connected — closing the "静默连错" hole on non-preferred ports, not just on the preferred one.

### Decision 3: Recovery waits on the resolved port, not the preferred port

`_build_recovery_session` and the cold-start launched session currently carry `base_url=preferred`. When the recoverable/launched Editor is mid-startup, its bound port may not yet answer; the wait loop must re-run the range scan until a matching ready endpoint appears (or the readiness timeout elapses), then bind the session to that resolved endpoint. The wait becomes "wait for a range-matched ready endpoint" rather than "wait for the preferred port to become ready".

### Decision 4: Scan range is shared, not re-hardcoded

The CLI must scan exactly the range the server binds within. Source the bounds from a single shared definition (preferred port + range length) rather than duplicating literals across client and session code, so the two stay coordinated if the range ever moves. Keep `DEFAULT_BASE_URL` as the preferred-first entry point.

### Decision 5: Bounded, fast, loopback-only probing

Probing 19 loopback ports with a short per-probe health timeout must stay cheap relative to the existing single-probe cost. Probes are loopback `127.0.0.1` only (matching the server's loopback binding), short-timeout, and stop early once a matching ready endpoint is found. The full range is only ever walked when nothing matches (the launch/timeout path), which is already the slow path.

## Risks / Trade-offs

- **[Two Editors report the same `project_path`]** (e.g., a stale half-dead Editor plus a fresh one) → claim the first `ready`/`ok` identity match in preferred-first order; liveness is proven by the live health response, and the session artifact is refreshed to the resolved endpoint so subsequent commands prefer it.
- **[Scan latency on the cold/miss path]** walking all 19 ports adds probe round-trips when nothing matches → bounded by a short per-probe timeout and only incurred on the launch/recovery path, which already tolerates startup latency; the hit path short-circuits on first match (preferred port stays first).
- **[Port reused by a different project between scan and use]** a matched endpoint could in principle change ownership → mitigated by the existing model that treats live identity as authoritative at use time and re-validates on persist; the artifact is a hint, not proof.
- **[Range drift between client and server]** if the CLI scanned a narrower/wider range than the server binds → mitigated by Decision 4 (single shared range definition).
- **[Regression risk to the working single-instance path]** preferred-first ordering and unchanged base-url mode keep the common path behaviorally identical; real-host regressions cover the non-preferred-port and rollover paths explicitly.

## Open Questions

- Should the scan probe candidates **sequentially** (preferred-first, stop on match) or **concurrently** with a short deadline? Sequential keeps the common case identical and is simpler; concurrency only helps the rare full-miss path. Leaning sequential unless host validation shows the miss-path latency is material.
- On the recovery/cold-start wait, should each poll re-scan the **full** range or lock onto the **first** non-preferred port that shows a matching PID/health signal once seen? Re-scanning is simplest and robust to rollover; locking is cheaper but risks re-pinning a single port. Leaning re-scan with first-match short-circuit.
