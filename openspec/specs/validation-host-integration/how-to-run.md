# Running Tests

## Test Layers

This repository has two distinct test layers:

**Mocked and helper-tool unit tests** (default):
```
python -m unittest tests.test_cleanup_validation_host_tool tests.test_cli_version tests.test_direct_exec_client tests.test_editor_log_isolation tests.test_openspec_backlog tests.test_openspec_change_meta tests.test_openspec_spec_hygiene tests.test_package_layout tests.test_prepare_validation_host_tool tests.test_refresh_change_signal tests.test_unity_log_brief tests.test_unity_puer_session tests.test_unity_session tests.test_unity_session_cli tests.test_unity_session_modules
```
Cover parsing, payload contracts, status codes, packaging checks, OpenSpec tooling, and local validation-host helper logic. Run without Unity Editor or a validation-host project.

`tests.test_openspec_spec_hygiene` is a pure-Python structural guard over `openspec/specs/**/spec.md`: it mirrors only two stable validator rules (every requirement needs a `#### Scenario:` and a `SHALL`/`MUST`) so this class of drift fails the default suite without the `openspec` CLI on PATH. It is not a substitute for the CLI — `openspec validate --all` remains the authority for full spec validation.

This is the same default suite executed by the repository's GitHub Actions unit-test workflow for pull requests and pushes to `main`.

**Real-host integration tests** (`tests/test_real_host_integration.py`):
Require a live Unity Editor and a prepared validation host project. Not executed unless explicitly enabled — they skip silently when prerequisites are not met.

## Running Real-Host Regression

Prerequisites:
- `UNITY_PROJECT_PATH` points to the validation host Unity `Project/` directory (set in environment or `.env`)
- Unity Editor is resolvable on this machine
- If this host needs extra Unity switches to start interactively (for example
  `-force-gles30`), set `UNITY_PUER_EXEC_UNITY_LAUNCH_ARGS` to a JSON array of
  strings in the same environment or `.env`:
  ```
  UNITY_PUER_EXEC_UNITY_LAUNCH_ARGS=["-force-gles30"]
  ```
  CLI auto-launch of the host picks this up without per-command flags. The
  tokens are appended after the CLI-owned `-projectPath`, activation switch, and
  project-private `-logFile`. They cannot rebind those CLI-owned switches.
- Validation host has been wired to the local package via `tools/prepare_validation_host.py`
- The helper output reports `"embedded_package_shadowing": false`. If it reports `true`, an immediate child of `Project/Packages/` declares `com.txcombo.unity-puer-exec` in its `package.json`, which can cause Unity to load that embedded copy instead of the repository-local package path in `manifest.json`; resolve or intentionally account for that before treating the run as evidence for current repository code. `"embedded_package_path"` names the first such directory and `"embedded_package_paths"` names all of them.

  Unity identifies an embedded package by the `name` declared in its `package.json`, not by the directory name. **Renaming the directory does not clear the shadow** — a directory renamed to `com.txcombo.unity-puer-exec.bak` is still loaded as `com.txcombo.unity-puer-exec`. Clearing the shadow requires **moving or removing the directory out of `Project/Packages/`** entirely.

Run command:
```
UNITY_PUER_EXEC_RUN_REAL_HOST_TESTS=1 python -m unittest tests.test_real_host_integration
```

### One Editor per suite (host reuse)

Each real-host class brings the Editor up **once** in a class-level fixture
(`_SharedRealHostDevice.setUpClass`), through the same
`real_host_retry.warm_up_with_retry` path the per-case model used, and stops it
once in `tearDownClass` — including when a case fails, so a broken case cannot
leak a running Editor into the next invocation. Ordinary cases reuse that
Editor; adding a case no longer adds a full Editor launch.

Per-case isolation is a **reset**, not a relaunch. `setUp` resets the state a
reused process can carry that a killed process could not:

- **Filesystem** — repository-owned validation temp assets (including probe
  subdirectories) are removed.
- **Modal dialogs** — a residual blocker left up by a previous case is resolved
  with an explicit cancel-like click, so it cannot block the next case's exec.
- **Play mode** — the Editor is returned to edit mode, and the case fails loudly
  if it will not leave play mode.
- **Compile state** — a compile-error case removes its broken source, but the
  change tracker does not treat a deletion as a compile-triggering change, so a
  reused Editor can stay stuck on the stale error. The reset touches a
  repository-owned probe to force the recompile and waits it out. The endpoint
  is re-resolved on every attempt because a reload can rebind the control port.
- **Change signal** — the test-owned import-change tracker is re-installed and
  re-settled so the next case starts from `not_pending`. When health already
  reports a settled signal this is skipped, so an ordinary case pays no extra
  full-filesystem walk.

### Cases that own their own boundary

Four cases need a process the shared Editor cannot be, and are listed in
`RealHostIntegrationTests.OWN_HOST_BOUNDARY_TESTS` with the pre-state they need
(`"stop"` or `"running"`):

| Case | Boundary | Why |
|---|---|---|
| `test_batch_mode_process_follows_uniform_activation_rule_against_real_host` | `running` → stops lazily | launches its own one-shot `Unity.exe -batchMode` processes and needs the exclusive project lock; it stops the shared host only after its skip check |
| `test_control_port_rolls_over_when_preferred_port_occupied_against_real_host` | `running` | asserts the later-port rollover (P1) whenever the preferred port is occupied, and stages the binder's mid-reload win (P2) only when the port is free for it |
| `test_exec_discovers_rolled_over_control_port_against_real_host` | `running` | asserts range-aware discovery of the same later-port endpoint (P1) and stages the same rollover (P2) when it can |
| `test_cold_launch_retries_on_transient_failure_against_real_host` | `stop` | asserts the cold-launch retry boundary itself, which needs a stopped host to observe |

Each such case reports the boundary it owned in a machine-usable
`_own_boundary_report` (`mode`, `stopped`/`perturbed`, and the observed result).
Their `setUp` no longer stops a host that a case will only skip, and the shared
host is restored after them — reusing a healthy Editor when the case's own
launch left one, and relaunching only when it did not.

A case that later discovers it needs a pristine process is added to that map and
says why, rather than silently failing only on reuse.

### Shared-host failure semantics

A shared host that dies mid-suite is detected by the per-case health scan. The
suite first gives a mid-reload Editor a chance to come back, then re-establishes
the host through `real_host_retry.warm_up_with_retry` within its bounded budget.
If it cannot, the case fails with the recorded `attempt_count`,
`last_launch_status`, and per-attempt history rather than reporting a pass
against a host that was not running.

### Activation is required for a controllable host

The control service no longer starts implicitly when the package loads. A process is
controllable only when activation has been requested for that process:

- **CLI-driven launch** (`launch_unity` / any project-scoped command that starts the
  Editor) always passes `-unityPuerExecControl` and a project-private `-logFile`, so
  a suite-launched host is controllable and privately observable with no extra flags.
- **Batch-mode launches** follow the same rule: without the switch the service does
  not start; with the switch it does. There is no batch-mode-only exception.
- **Hub / direct launches** without the switch and without the menu action leave the
  Editor not under CLI control. The CLI reports that condition rather than attaching
  to whatever answers a candidate port.

An Editor a human already opened on the host project without activation is therefore
**not** a usable real-host target. Close it (or use the Editor menu action
`Tools/UnityPuerExec/Activate CLI Control (this session)` / `Restart with CLI Control`)
and let the suite launch the host itself.

### Launch modes: control, isolation, or both

| How the Editor was started | Control service | Log isolation | Typical use |
|---|---|---|---|
| CLI launch (`launch_unity`) | yes (`-unityPuerExecControl`) | yes (project-private `-logFile`) | real-host suite, agent/CLI workflows |
| Command-line switch + `-logFile` | yes | yes | scripted relaunch, "Restart with CLI Control" |
| Menu "Activate CLI Control (this session)" | yes (session-scoped) | no — log was fixed at process start | escape hatch for a Hub-opened Editor |
| Menu "Restart with CLI Control" | yes | yes — relaunches with switch + isolated log | one-click return to the controlled state |
| Hub / direct, no activation | no | no (shared per-user `Editor.log`) | everyday editing; not a CLI target |

Mid-session menu activation grants control but never isolation: Unity binds
`Application.consoleLogPath` at process start, and there is no runtime redirection
API. That is why the menu activation is session-scoped (`SessionState`) and is never
remembered across Editor restarts. For isolation, relaunch with `-logFile` (CLI
launch or "Restart with CLI Control").

### Project-local session boundary

The suite decides whether the host project is free from project-local state alone:

- the project's Unity lockfile (held ⇒ an Editor is still serving the project)
- the Editor-published endpoint at `Temp/UnityPuerExec/endpoint.json` (present only
  when that Editor activated a control service; authorship is the Editor's, not the
  CLI's)

A clean starting boundary means the lockfile is not held. Unrelated Unity Editors
open on other projects do not affect that decision and are never kill targets. The
suite force-stops only the host project's own published process id when one is
named.

### A concurrent unrelated Editor and the shared per-user log

A Unity Editor started without `-logFile` — which is every Editor opened from Unity
Hub — writes to the single per-user log at `%LOCALAPPDATA%\Unity\Editor\Editor.log`.
That file is per *user*, not per *project*, so two Editors open on two different
projects are bound to the same file and each one rotates and truncates it under the
other. Byte-offset observation across a file being rewritten by a second process is
meaningless: a `log_range` recorded moments earlier can point past the current end
of file, and content the validation host really did emit can be absent entirely.

The suite is safe to run in that condition because it brings the host up through a
**host-private log**. The CLI launches the validation host Editor with `-logFile`
pointing at `<project>/Temp/UnityPuerExec/Editor.log`, and that Editor reports the
same path back through `/health` as `console_log_path` and through the published
endpoint. The CLI ranks the published path above the platform default when resolving
the effective log source, so individual cases observe it without each supplying
`--unity-log-path`. A development machine with several Unity projects open at once
is therefore a supported environment for real-host validation.

This does **not** extend to an Editor a human opened from Unity Hub and left running
on the host project without activation (see above). Even after mid-session menu
activation, that process still shares the per-user log. Close the unrelated Editor,
or let the suite launch the host itself.

### Recognizing an invalidated log source

The symptom is a **log-observation wait that times out with no matched content** —
`wait-for-log-pattern` or `wait-for-result-marker` returning `unity_not_ready` after
its full timeout, while the exec that should have produced the output reports
success. `test_exec_checkpoint_observation_chain_against_real_host` is the case that
surfaces this first.

Distinguish an invalidated log source from a product regression before bisecting:

- Check `log_offsets_invalidated` in the failing response. Present means the supplied
  start offset was past the end of the observed log — the file was rotated or
  truncated, and the offsets stopped denoting the intended content.
- Run `unity-puer-exec get-log-source --project-path <host>` and read
  `result.resolution_tier`. `published_endpoint` (or an explicit caller flag) means
  the observed path was stated by an authority; `platform_default` means it was
  assumed, and an assumed path on a multi-Editor machine is very likely the wrong
  file. Also read `result.observation_reliability` — a degraded report means the
  session is controllable but its log is the shared per-user default.
- Compare `result.path` against the per-user `Editor.log`. If they are the same file
  and more than one `Unity.exe` is running, the observation target is shared.
- Grep the observed log for `[UnityPuerExec] Ready on port`. One occurrence with two
  live bridges means two Editors are writing to one file.

A wait timeout under any of those conditions is an invalidated log source, not a
regression in the CLI chain or the runtime.

### Control-port binding coverage prerequisites

Two cases in this suite assert control-port binding behavior and have extra
process-state prerequisites beyond the shared ones above:

- **Batch-mode uniform activation rule**
  (`test_batch_mode_process_follows_uniform_activation_rule_against_real_host`):
  the host project must **not** be open in an interactive Editor. This case
  launches its own one-shot `Unity.exe -batchMode -nographics -quit` processes —
  once without `-unityPuerExecControl` (service must not start) and once with it
  (service must start and bind a port). Both need the exclusive project lock; the
  case `skip`s (does not fail) when any Unity process is already running. The
  suite's setUp force-stops the host Editor, so this normally holds — but if you
  keep the project open in your own Editor it will skip.
- **Occupied-preferred-port rollover**
  (`test_control_port_rolls_over_when_preferred_port_occupied_against_real_host`)
  and **rolled-over discovery**
  (`test_exec_discovers_rolled_over_control_port_against_real_host`):
  need an interactive Editor and a preferred control port (`55231`) that is
  occupied. The occupied port is the condition these cases exist to exercise, so
  they **run** when it is already held — including by another project's ready
  Editor — rather than skipping. The suite then asserts the part it can observe
  (P1): the host project's service is ready on a later port in the bounded range,
  and (for the discovery case) `exec --project-path` with no `--base-url` discovers
  that endpoint. When `55231` is free, the test is still autonomous: it runs a
  retry-binder for `55231` and forces a domain reload (via `exec` of
  `UnityEditor.EditorUtility.RequestScriptReload()`, with a touched-script
  fallback: the written `.cs` triggers the automatic code-change refresh, which
  starts compilation and the reload) so the binder wins the port in the
  `Stop()`→`Start()` window. No operator step is required.

  Two dispositions are distinct here and must not be read as a skip:

  - A mid-reload rebind race (P2) can only be staged when the suite's binder can
    contend for `55231`. Held by something the suite cannot displace (another
    project's Editor or an unrelated process), the case still asserts P1 and its
    boundary record states `mid_reload_rebind=not_staged` together with
    `preferred_port_held_by`.
  - If the host was launched successfully but the suite's own endpoint oracle still
    cannot see its ready endpoint anywhere in the bounded range after bounded
    retries, the case **fails** and reports the bound launch outcome and the ports
    probed. That is an endpoint-discovery observation, not a missing prerequisite.

  The cases skip only when the expectation cannot be evaluated at all — the gate is
  disabled, Unity or the host project is absent, or a required trigger cannot be
  staged for reasons outside the suite's control (for example a free preferred port
  whose `Stop()`→`Start()` window the binder loses).

## Result Interpretation

| Result | Meaning |
|--------|---------|
| `run` | The condition the expectation exists to exercise. The occupied-preferred-port rollover cases run — and assert the later-port rollover (P1) — whenever `55231` is already occupied, including by another project's ready Editor. Not a skip and not a failure. |
| `fail` / `error` | Prerequisites were satisfied but the CLI chain, runtime, log observation, or assertion failed; or a launched host's own ready endpoint could not be observed in the bounded control-port range after bounded retries. This is a real-host regression. |
| `skip` | The expectation cannot be evaluated at all: the real-host gate is disabled, `UNITY_PROJECT_PATH` is missing, Unity or the host project/manifest is absent, or a required trigger cannot be staged for reasons outside the suite's control. Not a product regression. A partially-stageable case does not report `skip`: it asserts what it can and records the unstageable sub-assertion in its boundary record. |

Mocked test passes do **not** substitute for real-host regression. They protect parsing, payload, and local contract logic only.
The default GitHub Actions workflow excludes `tests/test_real_host_integration.py` on purpose; real-host coverage remains a separate manual validation path.

## Current Coverage Chain

The real-host regression exercises this primary chain:

```
exec --project-path ... -> use log_range.start -> wait-for-result-marker -> wait-for-log-pattern --extract-json-group
```

For the full set of runtime validation requirements this covers, see [spec.md](spec.md).
