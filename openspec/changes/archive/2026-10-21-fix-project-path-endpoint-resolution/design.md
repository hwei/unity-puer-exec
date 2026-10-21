# Design

## Context

See proposal.md (Why) for the two defects. The code facts this design relies on:

- `unity_session_env.resolve_project_path` returns `Path(project_path)` exactly as given. A relative argument stays relative all the way through to `session.project_path`, and the issue's payload shows `"project_path": "Project"`.
- `unity_session._payload_matches_project` compares with `normcase(normpath(...))` and never makes the path absolute. `unity_session_endpoint.paths_equal` already does the right comparison (`realpath`, which also expands 8.3 short names). It is used only for publication confirmation.
- The C# health and publication `project_path` is `Path.GetDirectoryName(Application.dataPath)`, which is absolute.
- `exec` survives today because `_make_published_endpoint_resolver` confirms the publication by session marker before it falls back to `discover_project_endpoint`. `_play_probe_endpoint` goes straight to `discover_project_endpoint` every time, so a relative path makes every probe miss. `_wait_for_play_state` then keeps `state = None` and returns `_play_running_result(..., None)` once the budget runs out. That is exactly the `play_state: null` / `running` loop in the issue. The same defect explains why the reporter's first `play` also returned `running`.
- `get_blocker_state` sets `base_url=direct_exec_client.DEFAULT_BASE_URL`, which is the preferred port 55231. In the issue that port belonged to the other Editor.

This is a follow-up to the archived Editor-publication discovery work. Its finding still holds: the Editor's publication is the authoritative identity source. The gap is that two call paths never adopted it.

## Goals / Non-Goals

**Goals:**
- A relative `--project-path` behaves identically to its absolute form in every ownership check.
- Play-mode probes use the publication-first resolution that readiness waits already use.
- A reported `session` triple is never assembled from two different Editors.

**Non-Goals:**
- No change to the C# publication or health payload.
- No new `--base-url` pinning advice for play-mode commands. `--base-url` already works, and the project-mode fix removes the reason to recommend it.
- No change to how modal blockers are detected. Detection is already keyed on the project's published pid.

## Decisions

### D1. Make the project path absolute once, at `resolve_project_path`

`unity_session_env.resolve_project_path` will return an absolute path: `Path(...).resolve()` for an explicit argument and for `UNITY_PROJECT_PATH`, relative to the process working directory. The cwd fallback is already absolute. Every downstream consumer then gets the absolute value, including publication reads, lockfile checks, `session.project_path`, and the log paths.

Alternative considered: fix only the comparison. That would leave `session.project_path` relative in payloads, and `{project_path}` `next_steps` templates would break when an agent runs them from another directory. Doing both is the safer choice.

### D2. Also compare ownership with `paths_equal`

`_payload_matches_project` will delegate to `unity_session_endpoint.paths_equal`. This is defence in depth for callers that pass paths without going through `resolve_project_path`, such as test helpers and `_make_recovery_endpoint_resolver`. It also handles 8.3 short names and the forward slashes in `Application.dataPath`.

### D3. Play-mode probe resolves publication-first

In project mode, `_play_probe_endpoint` will reuse one `_make_published_endpoint_resolver(resolved_project_path, health_timeout)` per command invocation. It is built once in `_run_play_mode_command` and threaded through `_post_play_mode`, `_wait_for_play_state` and `_stop_wait_for_compile`. The command then probes the resolved base URL for its health payload. The resolver's scan fallback locks onto the confirmed port, so steady state stays at one probe per poll. The probe reads the publication again on every tick, so a domain reload's new marker and port are followed without scanning.

Alternative considered: keep the scan and just fix the comparison. That would work for the reported case. It would still re-scan the whole port range on every poll, and it would keep play-mode on a different resolution model from exec. That divergence is how this bug went unnoticed.

### D4. Distinguish "endpoint unresolved" in the `running` payload

`_wait_for_play_state` will track whether any probe resolved a project-owned endpoint. `_play_running_result` will add `result.target_play_state` and `result.endpoint_resolved` (a boolean) to the payload. When `endpoint_resolved` is `false`, it will choose a distinct guidance `situation`: the project's endpoint could not be reached or identified, so check `get-blocker-state` / Editor liveness. The existing "exit has not settled" text is kept for the case where the endpoint was reached. `play_state` keeps its current meaning, the last observed state, which may be `null`. Existing fields are unchanged, so this is additive.

### D5. `get_blocker_state` reports the publication's endpoint

The session takes `base_url` from `publication["base_url"]` when a publication is present. Otherwise it is `None`, which serialises as `null`. The pid logic is unchanged. `resolve-blocker` shares this function, so it is fixed at the same time.

## Risks / Trade-offs

- [Absolute project path changes payload text] → `session.project_path` becomes absolute. That makes the payload more correct, and agents that echo it into `next_steps` gain from it. Any test that asserts the literal relative value is updated in the same task.
- [`Path.resolve()` follows symlinks/junctions] → The Editor reports a non-resolved `Application.dataPath`. A worktree reached through a junction could resolve to a different spelling from the one the Editor reports. D2's `paths_equal` uses `realpath` on both sides, so ownership still matches. Publication reads use the resolved path, which points at the same files.
- [`session.base_url` may be `null` for get-blocker-state] → Consumers that dereference it must handle `null`. It was never a correct value in that case, and the change is documented in help.

## Migration Plan

This is a CLI-only change that ships in the next package version. No host-side migration is needed. Rollback is a revert.
