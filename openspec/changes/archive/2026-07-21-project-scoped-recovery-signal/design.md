## Context

`ensure_session_ready` (`cli/python/unity_session.py`) decides, when no ready project-matched endpoint was discovered, whether to enter a recovery wait (`_has_recoverable_editor_signal`) or launch a new Unity Editor. Today that decision is `bool(artifact_pid_running or unity_pids)`, where `unity_pids` comes from `_list_unity_pids()` — every `Unity.exe` process on the host via `tasklist /FI "IMAGENAME eq Unity.exe"`, with no project scoping at all.

`diagnose-exec-endpoint-misroute` fixed the more severe defect this fed into (a project-scoped wait wrongly claiming an unrelated project's `ready` endpoint) but left this root heuristic unchanged, logging it as a `product-improvement` follow-up (see that change's `design.md` Decisions section and `results/validation-evidence.md`). Confirmed live: with an unrelated project's Editor running and the requested project having no session artifact, `ensure_session_ready` now safely times out instead of misrouting — but it never reaches `_launch_unity` for the requested project either, because the presence of *any* Unity process is (wrongly) read as "our project might be recovering."

This repository's process-liveness helpers (`unity_session_process.py`) are already Windows-only (`tasklist`, `taskkill`); this change keeps that assumption rather than introducing cross-platform abstraction.

## Goals / Non-Goals

**Goals:**

- Replace the system-wide `unity_pids` input to `_has_recoverable_editor_signal` with a signal that is genuinely scoped to the requested project, so an unrelated project's running Editor never causes a recovery wait (and resulting stall) for a different project.
- Keep the existing `artifact_pid_running` signal (the session artifact's own recorded PID) — it is already project-scoped.
- Preserve today's conservative bias: when the signal is ambiguous or the probe itself fails for a reason unrelated to lock contention, treat it as "possibly recoverable" (wait) rather than risk a duplicate launch racing Unity's own project lock.

**Non-Goals:**

- Cross-platform support. The probe is Windows-only (`msvcrt.locking`), consistent with the rest of `unity_session_process.py`.
- Changing `discover_project_endpoint`, `validate_endpoint_identity`, or the `wait_for_session` endpoint-resolver fix from `diagnose-exec-endpoint-misroute` — this change is scoped to the launch-vs-wait decision that runs *after* that discovery has already failed to find a ready match.
- Detecting *which* other process holds the lock, or surfacing its PID — only whether the requested project's own lock is currently held by someone.

## Decisions

**Use a non-blocking exclusive-lock probe against the project's own `Temp/UnityLockfile`, not pid enumeration or the existing `project_lock`/`fresh` diagnostic.**

Empirically verified against a real running Editor (`c3-client-game2`, pid live on this host) and a real not-running project (`c3-client-tree2`):
- Attempting `os.open(lockfile_path, os.O_RDWR)` against a project whose Editor is currently open raises `PermissionError` immediately — Windows refuses the second handle outright, because Unity opens this file with a sharing mode that denies concurrent access. No second-step lock call is even needed to detect this case, though the design still attempts one for the case where the open itself succeeds (see below).
- Against a project whose Editor is not running, `os.open` succeeds and a subsequent `msvcrt.locking(fd, LK_NBLCK, 1)` also succeeds (immediately released after acquiring), confirming no contention.
- Against a project whose `Temp/UnityLockfile` does not exist at all (never opened, or `Temp/` cleaned), `os.open` raises `FileNotFoundError` — must be distinguished from `PermissionError`: no file to hold a lock on means definitively not recoverable via this signal, not "ambiguous."

Alternatives considered and rejected:
- **Reuse `_project_lock_details(project_path)`'s existing `fresh` flag** (already computed at every `ensure_session_ready` call site, currently only used for diagnostics). Rejected: `fresh` is bounded by `PROJECT_RECOVERY_WINDOW_SECONDS` (30 seconds) — a crash-recovery window, not a liveness check. Any Editor session open longer than 30 seconds (i.e., practically all of them) would read as "not fresh," causing the *opposite* failure: a legitimately-open Editor for the requested project would look "not recoverable," and the code would call `_launch_unity` against a project Unity already has locked — a real project-lock conflict, worse than today's stall.
- **Filter `_list_unity_pids()` by inspecting each PID's command line for a matching `-projectPath` argument** (e.g. via `wmic process get processid,commandline` or `Get-CimInstance Win32_Process`). Rejected as the primary mechanism: heavier (a second process-enumeration call, more fragile string parsing of command lines), and the lockfile probe already gives a direct, binary, race-free answer without needing to parse Unity's invocation arguments.
- **pywin32 `win32file`/`win32con` locking APIs** for more explicit Windows semantics. Rejected: `msvcrt.locking` is stdlib, requires no new dependency, and the empirical test above shows it (plus the `os.open` `PermissionError` path) is already sufficient to distinguish all three cases correctly.

**Signal composition:** `_has_recoverable_editor_signal` becomes `artifact_pid_running or _project_lockfile_is_held(project_path)`, where `_project_lockfile_is_held`:
1. Returns `False` immediately if the lockfile path does not exist (`FileNotFoundError` on open) — definitively not held.
2. Returns `True` if `os.open` fails for any other `OSError` (including `PermissionError`) — conservative: treat as held/ambiguous rather than risk a duplicate launch.
3. Returns `True` if `os.open` succeeds but the non-blocking lock attempt raises `OSError` — held by someone else.
4. Returns `False` if both the open and the lock attempt succeed — immediately release the lock and close the file; nothing else may write through this handle.

## Risks / Trade-offs

- **[A non-Unity process could transiently hold the file, e.g. an antivirus scanner or backup tool]** → Treating this as "recoverable" (wait, don't launch) is the conservative direction already baked into today's heuristic; worst case is a wait up to `ready_timeout_seconds` before falling through, not a duplicate launch or misroute.
- **[Windows-only]** → Matches this module's existing hard Windows dependency (`tasklist`, `taskkill`); no regression in supported-platform scope.
- **[Behavioral change to an existing decision path used by every `ensure_session_ready` call]** → Mitigated by keeping `artifact_pid_running` unchanged and only replacing the `unity_pids` term; add regression coverage for the existing recovery-vs-launch test scenarios (`test_ensure_session_ready_reuses_project_recovery_without_launching`, `test_ensure_session_ready_launches_when_lock_is_fresh_but_no_editor_is_recoverable`) alongside the new "unrelated project running, requested project's lockfile not held → launches" case.

## Migration Plan

1. Add `_project_lockfile_is_held(project_path)` to `unity_session_process.py` alongside the existing `is_pid_running`/`list_unity_pids` helpers, with unit tests covering the three `os.open`/lock outcomes via mocked `os.open`/`msvcrt.locking`.
2. Wire it into `_has_recoverable_editor_signal` in `unity_session.py`, replacing the `unity_pids` parameter with the new project-scoped check (the function's `unity_pids` argument becomes unused for this decision; verify no other caller still depends on the old signature's semantics).
3. Add regression tests for the "unrelated project running, requested project not recoverable → launches" scenario, and re-run the existing recovery/launch-conflict suite to confirm no regression.
4. Optionally confirm against the real host (`c3-client-tree2` + an unrelated running project) if the mocked reproduction leaves residual doubt.
5. Rollback is reverting the code change; no persisted state or protocol migration is involved.

## Open Questions

- ~~Should `unity_pids` remain as a parameter to `_has_recoverable_editor_signal` at all (e.g. for diagnostics/logging), or be dropped entirely from that function's signature?~~ **Resolved during implementation:** dropped. The function's only use of `unity_pids` was the truthy check being replaced; diagnostics already receive `unity_pids` independently via `_build_launch_coordination_diagnostics` at each call site, so nothing was lost. The signature is now `_has_recoverable_editor_signal(artifact_pid_running, project_path)`.
