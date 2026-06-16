# Host Validation Evidence

Real-host validation on Unity 2022.3.62f2 (Mono), project `douyin-unity-test`, 2026-06-16.
The package under test is the embedded copy in that project, synced to match the
repository-local fix (`UnityPuerExecServer.cs`).

## 3.1 — Port rollover on a Mono `SocketException` (occupied preferred port)

Before the fix (old code, `AssetImportWorker0.log`):

```
[UnityPuerExec] Unexpected error binding port 55231: System.Net.Sockets.SocketException (0x80004005): ...
[UnityPuerExec] Failed to bind any port in range 55231-55250. Last error: ...
  Start () at .../UnityPuerExecServer.cs:278
```

The generic `catch` hit a `SocketException` and `break`ed after only port 55231;
ports 55232-55250 were never tried.

After the fix (interactive Editor, PID 42012), with 55231 occupied at bind time:

```
[UnityPuerExec] Port 55231 unavailable: ...
[UnityPuerExec] Ready on port 55232
```

Live confirmation: `Get-NetTCPConnection` showed the interactive Editor (PID 42012)
listening on **55232** — a successful rollover instead of a hard failure. `/health`
on 55232 reported the douyin project identity.

## 3.2 — Batch-mode worker subprocesses do not start the service

A recompile restarted the persistent asset-import workers with the fixed code.
Two fresh workers (`AssetImportWorker2` PID 102664, `AssetImportWorker3` PID 23716,
both started 15:46:13, after the domain reload) each logged:

```
[UnityPuerExec] Skipping control service start in batch-mode process
  Start () at .../UnityPuerExecServer.cs:244
  .cctor () at .../UnityPuerExecServer.cs:201
```

Discriminators confirming this is the new code (not stale logs):
- New line numbers (`Start()` 244 = the guard; `.cctor` 201, shifted +1 by the added
  `using System.Net.Sockets;`). Old code logged at 278/286 and `.cctor` 200.
- No `Ready on port` and no `Failed to bind` lines in either worker log.
- `Get-NetTCPConnection` showed neither worker holding any port in 55231-55250.

## Combined outcome

With workers no longer squatting the preferred port, the interactive Editor reclaimed
**55231** on the subsequent recompile (was being pushed off it before the fix). This
is the end-to-end goal of the change: the preferred control port belongs to the
interactive Editor, and a busy preferred port now rolls over instead of failing.
