## Context

`tests/test_real_host_integration.py` (~831 lines, gated by `UNITY_PUER_EXEC_RUN_REAL_HOST_TESTS` and a resolved `UNITY_PROJECT_PATH`) drives the CLI exec/observation chain against an already-running interactive Unity Editor. The two binding behaviors we want to cover are NOT expressible through that exec chain:

- **Batch-mode skip** is observable only at process startup, in a non-interactive Unity process. It does not require the interactive Editor at all — a one-shot `Unity.exe -batchMode -quit -projectPath <host> -logFile <tmp>` run loads the editor domain, fires `[InitializeOnLoad]`, and the package logs the skip line. This is cheap to assert from the log file.
- **Port rollover** is a property of interactive `Start()` when the preferred port is already bound. Asserting it means: occupy the preferred loopback port from the test process, cause an interactive Editor `Start()` to run, then observe that the service came up on a later port (via `/health`) — none of which the current CLI chain does.

The two pieces therefore differ sharply in automation cost. The manual validation already performed for `fix-control-port-bind-fallback` is the reference behavior to encode.

## Goals / Non-Goals

**Goals:**
- A repeatable, opt-in real-host assertion that a batch-mode process logs the skip line and binds no control-range port.
- A repeatable, opt-in real-host assertion that an occupied preferred port produces rollover (service ready on a later port) rather than a whole-scan failure.
- Zero impact on the default mocked/unit CI workflow; clean skips when prerequisites are missing.

**Non-Goals:**
- No product/runtime code changes.
- No attempt to assert binding behavior from within the CLI exec protocol (it has no such surface).
- No coverage of multi-interactive-Editor port arbitration beyond single-rollover.

## Decisions

### Decision 1: Batch-mode skip via a standalone batch-mode launch + log assertion

Add a test that launches `Unity.exe -batchMode -nographics -quit -projectPath <host> -logFile <tmp.log>`, waits for exit, and asserts the log contains `Skipping control service start in batch-mode process` and does NOT contain `Ready on port` or `Failed to bind any port`. Optionally sample `Get-NetTCPConnection`/`netstat` during the run to assert no control-range bind, but the log assertion alone is decisive.

- Rationale: This is the closest automatable analog to the manual worker-skip proof, and it is self-contained (own project lock, own log file). It does not need — and must not collide with — a running interactive Editor on the same project.
- Constraint: the host project must not already be open in an interactive Editor (project lock). The test must detect that and skip rather than fail.
- Alternative considered: force a real AssetImportWorker to spawn from the interactive Editor and read its worker log. Rejected as non-deterministic (worker scheduling depends on pending import work) — exactly the flakiness seen during manual validation.

### Decision 2: Port rollover via a retry-binder racing the Stop→Start window of a forced domain reload

`Start()` re-runs on every domain reload (it is called from the `[InitializeOnLoad]` static constructor). Triggering a reload is therefore the lever, and it is NOT the hard part — there are two viable triggers:

- **Programmatic (preferred, fully autonomous):** issue an `exec` through the existing control endpoint that calls `CS.UnityEditor.EditorUtility.RequestScriptReload()`. This forces a domain reload with no GUI focus and no temp file. The exec response may surface as a benign disconnect because the reload tears down the ScriptEnv; the test tolerates that and keys off the post-reload health instead.
- **Focus-driven (fallback):** bring the Editor window to the foreground via win32 `SetForegroundWindow` after touching a host script, so Unity's auto-refresh recompiles and reloads. This is exactly what the manual validation used.

The actual subtlety is the port handoff, not the trigger. At steady state the Editor itself holds 55231, so the test cannot pre-occupy it. The reload sequence is `beforeAssemblyReload → Stop()` (releases 55231) → domain reload → `Start()` (rebinds). The test runs a **retry-binder** that polls to bind 55231 continuously; during the multi-second reload it wins the freed port before `Start()` runs, forcing `Start()` to roll over to 55232. The test then asserts a ready `/health` on the later port (`port`/`base_url` identity) and releases the binder.

- Rationale: This is the exact procedure already proven during the `fix-control-port-bind-fallback` manual validation — the retry-binder reliably won the Stop→Start window. The reload window is seconds wide versus a sub-millisecond bind attempt, so the race is dependable rather than flaky.
- Robustness: handle the case where 55231 is held by an unrelated process at test start (skip with reason), and always release the binder in teardown so the Editor reclaims 55231 on its next reload.
- Alternative considered: add a debug-only HTTP endpoint to re-trigger `Start()`. Rejected — adding product surface purely for a test contradicts the no-runtime-change goal; `RequestScriptReload` already exists.

### Decision 3: Reuse existing gating and skip discipline

Both tests live in `tests/test_real_host_integration.py`, reuse `_real_host_tests_enabled()` / `_require_real_host_project_path()` / `_require_unity_editor()`, and skip (not fail) when Unity, the host project, or the required process state is unavailable — consistent with the existing suite and the "remains outside the default unit-test workflow" requirement.

## Risks / Trade-offs

- [Batch-mode test needs the host project NOT open interactively, but real-host runs often have it open] → Mitigation: detect an existing interactive lock/open editor and skip with a clear reason; document the ordering in `how-to-run.md`.
- [Retry-binder loses the Stop→Start race and the Editor rebinds 55231] → Mitigation: the reload window is seconds wide vs a sub-ms bind; poll continuously and, if 55231 is still claimed by the Editor after the reload settles, retry the reload once before failing with a clear diagnostic.
- [`RequestScriptReload` exec returns a disconnect because the ScriptEnv tears down] → Mitigation: treat the disconnect as expected and key the assertion off post-reload `/health`, not the exec response.
- [Port occupation could collide with a real running service on 55231] → Mitigation: the test owns and releases the port deterministically and skips with a reason when 55231 is already held by an unrelated process at start.

## Migration Plan

- Test-only addition; no rollout/rollback concern beyond reverting the test file and spec delta.
- Update `openspec/specs/validation-host-integration/how-to-run.md` to describe the batch-mode run prerequisite (host project not open) and any operator-assisted step for the rollover case.

## Open Questions

- Does `exec` of `CS.UnityEditor.EditorUtility.RequestScriptReload()` reliably force a full domain reload (and thus a `Start()` re-run) on the host Unity version? If a PuerTS binding or timing quirk prevents it, fall back to the win32 focus + touched-script trigger. Resolve during implementation; either trigger keeps Decision 2 fully autonomous.
