### 7.1 Real-host evidence — 2026-09-20 (validation host tree2, Unity 2022.3.62f2)

Environment: repository package wired via manifest (embedded shadow removed earlier in
this session), host restarted fresh for each probe run.

Watcher/signal findings (decisive):
- Unity Editor's embedded Mono on Windows delivers zero FileSystemWatcher events on
  startup (in-process probe across Assets/ and Temp/: watcher bound, raising enabled,
  zero callbacks; the same watcher outside the editor fires instantly). Raw events DID
  arrive later in some sessions — delivery is delayed/unreliable, not absent — so the
  watcher cannot be the primary signal source on this platform.
- Fix: the incremental scan (dir-mtime gated, per-directory snapshot with known-code-
  file re-stat for in-place edits) is the real signal source; the watcher is an
  accelerator only. Warm scan cost ~0.3-0.8s over ~120k entries (project tree2); the
  ~9-11s cold first scan lands once per session inside the warmup exec.

Triggered-refresh evidence (exec1 after writing Assets/AutomaticRefreshProbe.cs):
{"triggered": true, "reason": "compile_triggering_change",
 "paths_changed": ["F:/.../Assets/AutomaticRefreshProbe.cs"],
 "settle_outcome": "dispatched", "elapsed_ms": 531}
Terminal exec1 completed in ~54s including the full compile cycle; second exec:
{"triggered": false, "skipped_reason": "no_pending_change"} — the loop-breaking
property holds. False-positive rate in these runs: 0 (non-code writes never trigger).

Real-host suite: RefreshOnChangeRealHostTests 4/4 OK (330s). Mock suite OK.
openspec validate refresh-on-change: valid.
