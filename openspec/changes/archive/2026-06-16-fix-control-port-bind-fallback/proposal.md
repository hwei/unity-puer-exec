## Why

The Unity Editor server's bounded port-fallback scan never works under Unity's Mono runtime: Mono's `HttpListener` is a managed socket implementation that throws `SocketException` (not `HttpListenerException`) when a port is in use, so the retry loop hits the generic `catch` and `break`s after the very first occupied port. The service therefore fails to bind whenever the preferred port `55231` is taken, while ports `55232-55250` sit idle — directly violating the existing `project-control-endpoint` requirement that occupied-preferred-port must roll over to later ports.

This is compounded by `AssetImportWorker` subprocesses: `[InitializeOnLoad]` runs in every Unity process, including batch-mode asset-import workers, so a transient worker can win the race for the preferred port `55231` and squat on it, leaving the main Editor (and other workers) to fail. Observed in the field: `AssetImportWorker1` held `55231` while `AssetImportWorker0` logged `Failed to bind any port in range 55231-55250` after trying only `55231`.

## What Changes

- Fix the port-fallback loop so a bind failure caused by an already-in-use port (`SocketException`, including Mono's `SocketError.AddressAlreadyInUse`, as well as `HttpListenerException`) causes the loop to `continue` to the next candidate port instead of aborting the whole scan.
- Reserve `break` (hard abort) only for genuinely fatal, non-contention errors, and make the final failure message reflect how many ports were actually attempted rather than implying the full range was scanned.
- Skip starting the control service in non-interactive Unity processes (batch mode / `AssetImportWorker` subprocesses) so transient import workers no longer contend for or squat on the preferred port. The interactive Editor remains the sole owner of the endpoint.

## Capabilities

### New Capabilities
<!-- None: this change corrects behavior governed by an existing capability. -->

### Modified Capabilities

- `project-control-endpoint`: Strengthen the "selects an available loopback port" requirement so it explicitly mandates rolling over on a port-in-use error regardless of the concrete exception type the host runtime raises (covering Mono's `SocketException`), and add a requirement that the control service only starts in the interactive Editor process, not in batch-mode / asset-import worker subprocesses.

## Impact

- Unity package Editor server: `packages/com.txcombo.unity-puer-exec/Editor/UnityPuerExecServer.cs` — the `Start()` bind loop (`catch` arms / loop control) and an early-out guard for batch-mode processes.
- No CLI or protocol wire-format changes; health identity fields are unaffected.
- Tests/validation: real-host validation should exercise the occupied-preferred-port rollover path on Unity/Mono and confirm worker subprocesses no longer bind a port. See `openspec/specs/validation-host-integration/how-to-run.md`.
