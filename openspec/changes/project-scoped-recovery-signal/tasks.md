## 1. Lockfile Probe

- [x] 1.1 Add `_project_lockfile_is_held(project_path)` to `cli/python/unity_session_process.py`: attempt `os.open(unity_lockfile_path(project_path), os.O_RDWR)`; return `False` on `FileNotFoundError` (no lockfile, definitively not held); return `True` on any other `OSError` (conservative: treat as held); on success, attempt a non-blocking `msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)`, returning `True` if that raises `OSError` (held by someone else) or `False` if it succeeds (release the lock and close the file before returning).
- [x] 1.2 Add unit tests for all four outcomes (missing file, permission-denied open, lock-contention on an opened file, and clean acquire-then-release) using mocked `os.open`/`msvcrt.locking`, not real Unity processes.

## 2. Wire Into Recovery Decision

- [x] 2.1 Update `_has_recoverable_editor_signal` in `cli/python/unity_session.py` to use `artifact_pid_running or _project_lockfile_is_held(project_path)` instead of the system-wide `unity_pids` check. Decide, based on what remains true, whether `unity_pids` stays in the function's signature for diagnostics or is dropped.
- [x] 2.2 Update all call sites of `_has_recoverable_editor_signal` in `ensure_session_ready` accordingly.

## 3. Regression Coverage

- [x] 3.1 Add a regression test: requested project has no session artifact and is not running; an unrelated project's Editor is running (simulated via pids) but the requested project's own lockfile is not held (simulated via the mocked probe) → `ensure_session_ready` proceeds to `_launch_unity` for the requested project instead of entering a recovery wait.
- [x] 3.2 Add a regression test: requested project's own lockfile is held (simulated via the mocked probe), no artifact pid — `ensure_session_ready` still enters the recovery wait rather than launching a duplicate.
- [x] 3.3 Re-run the existing recovery/launch-conflict test suite (`test_ensure_session_ready_reuses_project_recovery_without_launching`, `test_ensure_session_ready_launches_when_lock_is_fresh_but_no_editor_is_recoverable`, and related `ensure_session_ready` tests in `tests/test_unity_session.py`) to confirm no regression.

## 4. Validation and Closeout

- [x] 4.1 Run the focused Python test suites relevant to `unity_session.py` (`tests.test_unity_session`, `tests.test_unity_session_cli`, `tests.test_unity_session_modules`, `tests.test_unity_puer_session`).
- [x] 4.2 Optionally confirm against the real host: an unrelated project's Editor already running, the requested project (`c3-client-tree2/Project`) with no session artifact and not running — confirm `exec` now launches tree2's own Editor instead of timing out.
- [x] 4.3 Run `openspec validate project-scoped-recovery-signal --strict --no-interactive` and confirm all tasks and evidence are archive-ready.
- [x] 4.4 Complete the required apply closeout review and record either `No new follow-up work identified` or human-discussed follow-up candidates in an allowed category.
