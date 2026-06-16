## 1. Fix the port-fallback bind loop

- [ ] 1.1 In `UnityPuerExecServer.Start()`, add a `catch (SocketException ex)` arm (alongside the existing `HttpListenerException` arm) that records `lastBindError`, closes the candidate, logs a warning, and `continue`s to the next port instead of aborting.
- [ ] 1.2 Restrict the generic `catch (Exception)` `break` to genuinely fatal, non-port-in-use errors so a single occupied port no longer aborts the whole scan.
- [ ] 1.3 Add `using System.Net.Sockets;` if not already present, and confirm the range-exhausted failure message is only emitted after every candidate port was actually attempted.

## 2. Skip the service in non-interactive processes

- [ ] 2.1 Guard `Start()` (or the static-constructor call site) with an early-out when `Application.isBatchMode` is true, so batch-mode / asset-import worker subprocesses do not start the listener.
- [ ] 2.2 Ensure the guard leaves all other lifecycle wiring intact for the interactive Editor (no listener leak, no double-start) and emits a concise log line when the service is intentionally skipped.

## 3. Validate on a Unity/Mono host

- [ ] 3.1 With the preferred port 55231 occupied by another listener, load the package in the interactive Editor and confirm it rolls over to 55232+ and reports the selected port via `/health` (per `openspec/specs/validation-host-integration/how-to-run.md`).
- [ ] 3.2 Trigger an asset-import worker (e.g. a reimport) and confirm via `Get-NetTCPConnection` / worker logs that no batch-mode worker binds a port in the 55231-55250 range.
- [ ] 3.3 Capture a short CLI/host transcript of the rollover and the worker-skip behavior as the change evidence.

## 4. Closeout

- [ ] 4.1 Update `meta.yaml` `updated_at` and confirm `assumption_state`/`evidence` still reflect reality after validation.
- [ ] 4.2 Run the apply closeout finding summary and recommend the `git commit` / `openspec archive` / final `git commit` sequence.
