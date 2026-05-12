## Context

The Unity Editor server currently binds a single hard-coded loopback endpoint, `http://127.0.0.1:55231/`. The Python CLI also defaults to that endpoint when preparing project-scoped sessions. Existing `launch_claim`, `UnityLockfile`, and pending-exec artifacts coordinate startup for one project, but they do not prevent unrelated Unity Editors on the same machine from contending for the same HTTP port.

The repository already has a project-local session artifact under `Temp/UnityPuerExec/session.json`. That artifact is a good place to persist the selected endpoint after readiness, but it must remain a candidate hint during cold start: old artifacts can survive process exit, project copies, or a later Editor taking the same port.

## Goals / Non-Goals

**Goals:**

- Let multiple Unity Editors that load the package run concurrently on one host without fighting over the same fixed control port.
- Preserve the existing preferred port for the first available service so simple direct-service workflows remain familiar.
- Make project-scoped CLI routing validate live endpoint identity before treating an artifact endpoint as authoritative.
- Include both `project_path` in the project artifact and `project_path` in `/health` so the endpoint can self-identify.
- Keep `--base-url` as an explicit direct target that does not imply project ownership or launch behavior.

**Non-Goals:**

- Do not introduce a long-running registry daemon or machine-global endpoint database.
- Do not make the CLI pre-allocate ports for Unity as the source of truth.
- Do not guarantee stable port numbers across Editor restarts.
- Do not change public exec, wait, or blocker command semantics except for the project-scoped endpoint discovery behavior.

## Decisions

### Service owns port selection

The Unity-side server will try to bind the existing preferred port first, then increment through a bounded loopback range until `HttpListener.Start()` succeeds. Binding, not a preflight socket check, is the authority because checking first would introduce a time-of-check/time-of-use race.

Alternative considered: have the CLI choose and pass a port at launch. That still fails when Unity discovers the port is unavailable after startup, and it does not help already-open Editors. A future launch argument can be added as a preferred-port hint, but the bound service port remains the source of truth.

### Health identity is the validation boundary

`/health` will return the selected `port`, `base_url`, `unity_pid`, `project_path`, and `session_marker`. The CLI must compare this identity with the requested project before using an artifact endpoint. A reachable ready service is not enough, because a stale artifact can point to a healthy service for a different project.

Alternative considered: rely on the artifact path to infer project identity. The path identifies where the hint was found, but it does not prove the live endpoint at `base_url` still belongs to that project.

### Session artifact remains project-local

The session artifact will persist the validated endpoint identity, including `project_path`, after readiness succeeds. It remains under the project `Temp/UnityPuerExec/` directory to keep cleanup and ownership aligned with the Unity project. During cold start, the CLI treats existing artifact data as a hint, probes it, and discards it for routing if live identity validation fails.

Alternative considered: write a machine-global map of project path to port. That would add cleanup, locking, and cross-user questions that the project-local artifact already avoids.

### Project mode uses validated candidates before fallback

Project-scoped CLI commands should prefer a live, validated artifact endpoint. If that fails, they may still use the existing launch/recovery coordination paths. During cold start after the CLI launches Unity, the CLI cannot assume an old endpoint; it must wait until the new server reports health and then persist the new endpoint.

### Direct base-url mode stays literal

`--base-url` remains an explicit direct-service selector. The CLI may inspect or invoke that endpoint, but it must not reinterpret it through project artifact ownership unless the command is in project mode.

## Risks / Trade-offs

- [Risk] A stale artifact points to another healthy UnityPuerExec service. -> Mitigation: require `/health.project_path` and session identity validation before project-mode routing.
- [Risk] Dynamic port scanning hides a real listener failure by skipping too aggressively. -> Mitigation: log each failed bind reason and fail clearly when the bounded range is exhausted.
- [Risk] Tests become timing-sensitive around cold start. -> Mitigation: keep most coverage in unit tests with injected health probes and artifact readers; reserve real-host validation for one representative non-default port scenario.
- [Risk] Existing direct users depend on the default constant. -> Mitigation: keep the preferred port as the first attempted port and preserve explicit `--base-url` behavior.

## Migration Plan

Implementation can be rolled out without a breaking schema migration. Older artifacts without identity fields are treated as unvalidated hints and can be refreshed after a successful health probe. If the new validation rejects an artifact, project mode falls back to launch/recovery rather than failing solely because the artifact is old.

## Open Questions

- What upper bound should the port scan use: a fixed count after `55231`, or a named min/max range?
- Should a future CLI option expose a preferred port hint for specialized direct-service workflows, or is `--base-url` sufficient?
