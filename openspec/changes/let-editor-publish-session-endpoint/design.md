## Context

This change follows directly from `isolate-validation-host-editor-log` (archived 2026-07-23) and revises several requirements it established. That change fixed one instance of a defect shape; this one removes the shape.

The shape is **a machine-scoped or historical fact standing in for a project-scoped, present one**:

| Instance | Stand-in | Truth | State |
|---|---|---|---|
| Log path | per-user `Editor.log` | the Editor's `Application.consoleLogPath` | fixed |
| `session.json` `unity_pid` | `list_unity_pids()[0]` | the ready payload's `unity_pid` | open |
| `ensure-stopped`, artifact present | a pid recorded earlier | any Editor now serving the project | open |
| `ensure-stopped`, artifact absent | `len(all Unity.exe) == 0` | this project's lockfile | open |

The evidence for the second and third rows was produced while applying the previous change: `_ensure_clean_test_boundary` obtained a `stopped` result from `ensure-stopped` while PID 85632 was alive and answering `/health` for the host project, so the case that followed attached to a Hub-launched Editor and observed the shared per-user log. The boundary helper is not at fault — it raises on failure (`test_real_host_integration.py:144`); it was told the host was stopped.

## Goals / Non-Goals

**Goals:**

- Make the Editor the only author of statements about the Editor.
- Make "which Editor serves this project, and how do I reach it" answerable from deterministic project-local files, with no port scan and no process-table correlation.
- Make control-service activation mean the same thing in every launch mode.
- Make the difference between a controlled Editor and a merely reachable one visible to a caller before it takes offsets, not after.

**Non-Goals:**

- Giving a mid-session-activated Editor an isolated log. See D4 — it is not achievable, and pretending otherwise is worse than naming it.
- Mirroring or re-emitting Unity log content. Rejected in the previous change's D2 and still rejected: `Application.logMessageReceivedThreaded` carries only managed-side messages, so a mirror silently drops native output that `wait-for-log-pattern` is expected to match.
- Preserving observability of a session after a clean Editor exit. See D2.
- Changing the exec protocol, the log-brief parser, or `brief_sequence` delimiting.

## Decisions

### D1: The Editor publishes `endpoint.json`; the CLI never writes a session record

On successful bind, the control service writes `Temp/UnityPuerExec/endpoint.json`:

```json
{
  "port": 55233,
  "unity_pid": 85632,
  "project_path": "F:/.../Project",
  "session_marker": "…",
  "console_log_path": "F:/.../Project/Temp/UnityPuerExec/Editor.log"
}
```

*Rationale.* Every field is taken from the running process — `Process.GetCurrentProcess().Id`, `Application.dataPath`, `Application.consoleLogPath` — so none of them can be a guess. This is the same principle that produced `console_log_path` in the previous change, applied to the rest of the record.

This is not `session.json` renamed. The distinction is authorship:

| | `session.json` (removed) | `endpoint.json` |
|---|---|---|
| Author | the CLI, about a process it does not own | the Editor, about itself |
| `unity_pid` source | machine-wide tasklist order | the process's own id |
| `console_log_path` source | the CLI's resolution at write time | `Application.consoleLogPath` |
| Can it be stale while present? | yes — the process may have changed since | no — it is removed when the service stops, and `Temp/` is removed on clean exit |

*Consequence that matters.* `is_pid_running` no longer gates session validity, which removes a real hole: it runs `tasklist /FI "PID eq N"` with no image-name filter, so a recycled pid belonging to any process reads as a live Unity session.

### D2: `Temp/` deletion on clean exit is a feature, not a limitation

Unity removes `Temp/` when the Editor exits cleanly and leaves it on a crash or a kill. The publication's lifetime therefore matches the cases in which it is wanted:

| Editor outcome | `Temp/` | Is the record wanted? |
|---|---|---|
| Clean exit | removed | No — nothing went wrong, and a surviving record would only offer a stale port |
| Crash | survives | Yes — and it survives |
| `taskkill /T /F` | survives | Yes — and it survives |

*Consequence that matters.* "No `endpoint.json`" becomes an unambiguous signal rather than a missing answer, and combined with the lockfile it decides the whole state space from local files:

```
Temp/UnityLockfile     Temp/UnityPuerExec/endpoint.json      Conclusion
──────────────────     ────────────────────────────────      ─────────────────────────────
    absent                     absent                        no Editor           → launch
    held                       absent                        Editor did not opt in → guide
    held                       present                       controlled          → connect
    absent                     present                       crashed/killed residue → readable,
                                                               relaunch required
```

`_project_lockfile_is_held` already distinguishes a held lockfile from a stale file via `msvcrt.locking`.

*A present publication is a claim, not a conclusion.* The `held + present` row is provisional: `Temp/UnityPuerExec/` survives a kill, and a human can then reopen the same project from Unity Hub without opting in — leaving a stale publication sitting next to a lockfile held by a different, uncontrolled process. Before the session is treated as controlled, the CLI confirms the publication against the live service: `/health` must answer on the published port and report the same `session_marker` and `unity_pid` the publication names. If the endpoint is unreachable or the identity does not match, the publication is residue, and with the lockfile held the state collapses to the "did not opt in" row. A recycled port must not be able to impersonate a controlled session, for the same reason a recycled pid must not (D1).

*Removal is quit-scoped, not stop-scoped.* The service stops on every domain reload (`UnityPuerExecServer.cs:213` hooks `Stop` to `AssemblyReloadEvents.beforeAssemblyReload`), so deleting the publication in `Stop` would open a window during every script compile in which `held + absent` reads as "did not opt in". The publication is therefore removed only on `EditorApplication.quitting`; across a reload it stays in place, momentarily naming a service that is restarting, and the confirmation step above covers that gap. For the same reason, the CLI does not conclude "did not opt in" from a single `held + absent` reading without allowing for a service-restart window.

*Trade-off accepted.* Reading a `log_range` from a cleanly exited session is no longer possible. A caller who needs a durable log passes `--unity-log-path` to a location outside `Temp/`, which already works.

### D3: Control-service activation is explicit, and uniform across launch modes

The service currently starts implicitly on Editor load and is suppressed in batch-mode (`UnityPuerExecServer.cs:275`). It becomes opt-in in every mode:

- **Command-line switch** — read from `Environment.GetCommandLineArgs()`. Process-scoped, so it survives domain reloads for free. The CLI passes it on every launch, so CLI users see no change.
- **Editor menu action** — for a process that was started without the switch. The opt-in is stored in `UnityEditor.SessionState`, which survives domain reloads and is cleared when the Editor process ends.

*Rationale.* One rule for all three launch modes replaces three different implicit behaviors. Batch-mode stops being a special case in the code and becomes a caller decision.

*Rationale for `SessionState` rather than `EditorPrefs`/`ProjectSettings`.* See D4 — a persisted opt-in would normalize a mode that cannot satisfy the observation contract.

### D4: Mid-session activation grants control but never isolation, and is therefore never remembered

A Unity process binds its log at startup from `-logFile`. `Application.consoleLogPath` is read-only and there is no runtime redirection API, so an Editor started without `-logFile` writes to the per-user `Editor.log` for its entire life. Mid-session activation delivers exactly half of what the CLI needs:

```
Control     (exec / health / reset)         can be granted mid-session   ✅
Isolation   (log_range / byte offsets)      fixed at process launch      ❌
```

Worse, the safety of the missing half depends on a condition outside the Editor: whether another Unity Editor is open and writing to the same per-user file. The capability is not merely degraded, it is *conditionally broken*, and the condition can change while a session runs.

*Rationale.* An option that cannot satisfy the observation contract must not become a remembered default. It is an escape hatch: explicit each time, session-scoped, and self-declaring.

*Self-declaring* is the operative part. Because `endpoint.json` carries `console_log_path`, the CLI can classify the session without guessing:

```
console_log_path == <project>/Temp/UnityPuerExec/Editor.log
      └─▶ fully controlled; observation is safe

console_log_path == a caller-chosen location (explicit -logFile at launch)
      └─▶ caller-directed; reported as reliable and attributed to the
          caller's explicit choice, not to a platform guess

console_log_path == platform default Editor.log
      ├─ this is the only Unity process on the machine
      │     └─▶ effectively private; usable, reported as degraded-by-origin
      └─ other Unity processes are running
            └─▶ byte offsets are unsafe; reported before the first observation
```

Classification compares normalized paths (case, separator, and Windows short-name normalization), so a platform-default log cannot escape its class by spelling.

The previous change reports offset invalidation *after* it happens (`log_offsets_invalidated`); this reports the hazard *before* a caller commits to offsets. The two are the same problem at opposite ends.

*Note on scope discipline.* The branch above counts every `Unity.exe` on the machine, which is a machine-wide question ("who else can write this per-user file") and therefore a legitimate use of a machine-wide count — unlike `ensure-stopped`'s current use of the same call to answer a per-project question.

### D5: `ensure-stopped` decides from the endpoint and the lockfile

The current rule reduces to "is the pid I recorded gone", with a fallback of "is the machine free of `Unity.exe`". Both are replaced by the D2 table: a project is stopped when its lockfile is not held. A published endpoint supplies the pid to stop when one is needed; a held lockfile with no endpoint is still a running Editor and is reported as such rather than killed blindly.

*Consequence that matters.* `ensure-stopped --immediate-kill` can no longer target a pid belonging to a different project.

### D6: The control-port scan survives only as an error-path diagnostic

With the endpoint published, the normal path is a single direct connection. Under this design a same-version service without a publication exists only as a failure mode, and `cli-version-compatibility` refuses a mismatched pair in `--base-url` mode with no bypass — so the scan can never produce an address worth handing to the caller to drive.

What it can still do is explain a refusal correctly. An Editor running an older bridge starts its service implicitly, publishes nothing, and has no opt-in menu action, so `held + absent` guidance that says "activate from the Editor menu" would point at a menu item that does not exist in that bridge. The 19-port scan (`55231`–`55249`) is retained solely so the error path can find such a service, read its old or absent `bridge_version`, and report `version_mismatch` — pointing the caller at an upgrade — instead of a missing opt-in. Its cost is paid only when the command is already failing.

## Open Questions

- **`EditorApplication.OpenProject` with arguments.** A second menu action, "Restart with CLI Control", could relaunch the Editor with `-logFile` and the activation switch, turning the escape hatch into a one-click return to the controlled state. This is **unverified** in this repository and Unity version. If it does not work as assumed, only the session-scoped activation action ships.
- **Publication atomicity.** `endpoint.json` must not be observable half-written. Write-to-temp-then-rename is the intended approach, pending confirmation that it behaves on Windows under a concurrently reading CLI.
- **Publication lifecycle at the edges.** Removal is quit-scoped by design (D2); two edges need real-host confirmation. First, whether the `EditorApplication.quitting` hook fires reliably enough that clean-exit residue stays rare — the D2 residue row already absorbs the cases where it does not. Second, whether Unity clears `Temp/UnityPuerExec/` when a project is reopened, which decides how long a stale publication can sit next to a new Editor's lockfile and therefore how load-bearing the D2 confirmation step is.

## Risks / Trade-offs

- **Large blast radius in `unity_session.py`.** ~85 references to `session_data`/`read_session_artifact` are concentrated there, and the artifact currently participates in recovery signalling and launch-conflict detection, not just addressing. → The D2 state table is intended to replace those branches wholesale rather than field-by-field; the risk is that a recovery path depends on artifact state in a way the table does not cover. Mitigated by keeping the existing real-host recovery cases as the acceptance bar.
- **A human who keeps a project open in Unity Hub loses the current silent-attach behavior.** → Intended and marked BREAKING. That behavior only appeared to work when exactly one Editor was open; when it was not, it produced the misattributed failure this change's evidence comes from. The refusal carries the two ways forward.
- **Clicking a menu item on every Editor start is friction.** → Accepted, and the friction is the point (D4). The low-friction path is letting the CLI launch the Editor, which is also the only path that yields isolation.
- **Batch-mode callers must now pass the switch to get a control service.** → Intended; it replaces an implicit suppression with a caller decision, and the batch-mode suppression test becomes a test of the default rather than of a special case.
- **`endpoint.json` could be mistaken for the removed `session.json`.** → D1 states the distinction explicitly; the durable spec should carry it so a later reader does not "restore" CLI-side writing as a convenience.
- **The lockfile ruling is Windows-shaped.** `_project_lockfile_is_held` decides via `msvcrt.locking`, and D2/D5 promote that probe to the sole arbiter of "stopped". → Acceptable while real-host validation is Windows-only; the durable spec states the rule as "the project lockfile is held", so a future platform port replaces the probe, not the contract.
