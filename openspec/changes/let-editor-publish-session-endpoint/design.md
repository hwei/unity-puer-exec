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

*Refinement found while applying: what "allowing for a restart window" actually is.*
D2 above says an unreachable publication is residue, softened by a restart window.
A fixed window alone cannot carry that, because the two cases it must separate are
not distinguishable by duration: a domain reload in a large project keeps the
service down far longer than any window short enough to fail fast, and the residue
case is permanent. Two discriminators are used instead, in order:

1. **A short grace window** (2 s) for the ordinary case where the listener is down
   for a moment, or the publication is mid-replacement.
2. **Whether the published process is still running.** A live published process
   next to a held lockfile is a controlled Editor whose service is restarting, and
   the caller's existing readiness wait — bounded by `ready_timeout` — is where
   waiting belongs. A published process that is gone, with the lockfile held by
   something else, is residue beside an Editor that never opted in.

Consulting the published process id here does not reintroduce what D1 removed. The
defect there was the CLI *inventing* a pid from tasklist order and then trusting it
as proof of liveness. This pid is stated by the Editor about itself, and it is only
ever corroboration alongside the project's own lockfile — never the sole evidence
that a session is live — so a recycled pid still cannot resurrect an ended session.

*Session marker, not process id, is the confirmation discriminator.* A `compiling`
health payload carries `session_marker` but not `unity_pid` or `project_path`, and
the marker is minted fresh on every service start, so it both proves identity and
lets a mid-compile Editor confirm. `unity_pid` and `project_path` are checked
additionally once the payload is `ready`.

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

## Resolved Questions

### R0: The activation switch is visible to the Editor — measured (task 1.1, partial)

Measured on the validation host with two batch runs of the same project, one with
`-unityPuerExecControl` and one without.

Without the switch the service does not start and the process says why. With it,
the same process binds and publishes:

```
[UnityPuerExec] Port 55231 unavailable: ...
[UnityPuerExec] Port 55232 unavailable: ...
[UnityPuerExec] Published endpoint at <project>/Temp/UnityPuerExec/endpoint.json
[UnityPuerExec] Ready on port 55233
```

So Unity passes an unrecognised switch through to `Environment.GetCommandLineArgs()`,
and the uniform activation rule holds in batch mode in both directions — which is
the evidence tasks 3.7 and 8.4 ask for. The rolled-over port is incidental but
useful: two unrelated Editors held 55231 and 55232, and the publication named the
port actually bound rather than the preferred one.

**Still unmeasured: survival across a domain reload.** A batch run compiles and
then loads the domain once, so it is not a vehicle for observing a reload. The
process command line cannot change within a process, so survival is expected on
structural grounds, but that is reasoning rather than evidence; task 8.9 is where
it gets measured. Task 1.1 stays open until then.

### R7: Menu-granted activation lives and dies with the process — measured (task 1.2)

Measured on the validation host with a Hub-launched (un-activated) Editor. Activating
via `Tools/UnityPuerExec/Activate CLI Control (this session)` greyed the menu item
(SessionState set, service started). A domain reload — one script edit — left it
greyed, so the mid-session activation survives a reload the same way the command-line
switch does. After killing the Editor and reopening the project without activation,
the menu item was clickable again: the SessionState opt-in did not restore into the
new process. That is D4's requirement that a menu-granted activation is explicit each
time, session-scoped, and never remembered across the project's next open — confirmed
rather than assumed.

### R6: A controlled launch publishes fields that match the live process — measured (task 8.2)

Measured by launching the host with the exact arguments the CLI's `launch_unity`
uses — the activation switch and a project-private `-logFile` — plus the project's
required `-force-gles30`. Once bound, every published field matched the running
process: the published `unity_pid` was a live process (the real Editor, not the
launcher), `project_path` matched, and `console_log_path` was the project-private
isolated log — not the per-user default, in deliberate contrast to R4's
menu-activated Hub Editor. `classify_session_state` confirmed `controlled` from a
single probe of the published port, with health `unity_pid`, `session_marker`, and
`project_path` all matching the publication. No port scan participated.

*Follow-up found (product-improvement, not this change's regression).* The CLI's own
`exec` launch of this host failed with `unity_start_failed` because `launch_unity`
has no way to pass a project-specific Unity argument, and this project needs
`-force-gles30` to start interactively. `launch_unity` has never had extra-argument
passthrough, so this predates the change — but the change makes the CLI-launch path
the primary supported path, which raises the stakes. A caller on such a project
currently cannot use CLI-driven launch. Candidate: an opt-in passthrough for extra
Unity launch arguments.

### R5: Hub-reopen and the refusal — measured (tasks 8.3, 8.6b, 1.6)

Continuing from R4's residue: the host was relaunched without activation (the
Hub-equivalent: `Unity.exe -projectPath <proj> -force-gles30`, no switch, no
`-logFile`), leaving it sitting next to the surviving residue publication.

- **1.6 — Unity clears `Temp/UnityPuerExec/` on reopen, very early.** The residue
  `endpoint.json` (old marker `1b0b6d13`, dead pid 71936) was already gone by the
  time the probe's first poll ran, within the Editor's startup. So a stale
  publication coexists with a new Editor's lockfile only for the earliest moments of
  startup, not indefinitely. The D2 confirmation step therefore mainly guards the
  *other* residue path — a kill followed by a different process taking the published
  port — rather than Unity's own reopen.
- **8.6b — the stale publication does not impersonate a controlled session.** With
  the residue cleared and the lockfile held by the un-activated Editor,
  `classify_session_state` returned `not_under_control`, not `controlled`.
- **8.3 — a project-scoped command refuses with actionable guidance.** `exec` against
  the un-activated host exited `17` (`editor_not_under_cli_control`) with three
  `ways_forward` entries, while four unrelated old-bridge Editors were running. It
  did not misreport `version_mismatch` and did not silently attach to another
  project — the pre-change failure mode. The controllable-with-a-non-private-log half
  of 8.3 is covered by R4's classification, where a menu-activated Hub Editor
  correctly reported the platform-default (non-private) `console_log_path`.

### R4: Residue and the stop boundary — measured (tasks 8.5, 8.6a)

Measured on the validation host with five Unity Editors running, one of them the
controlled host (pid 71936, identified from its own publication — pub pid == health
pid == 71936, matching marker). Killing it via `taskkill /PID 71936 /T /F`:

- The other four Editors survived. The kill reached only the published pid, which is
  the D5 property — a stop can no longer target a process belonging to another
  project.
- The publication survived the kill (`Temp/` is left on a kill), and with the
  lockfile now released `classify_session_state` returned `ended_residue`.
- `ensure-stopped` reported `stopped` (exit 0) with the four unrelated Editors still
  running — the machine-wide-count failure mode ("any unrelated Editor makes it
  report not-stopped forever") is gone.

*Note on the host's log class.* This host was Hub-launched and menu-activated, so its
published `console_log_path` was the platform-default per-user log, not an isolated
one — the D4 degraded-by-origin case, correct for a mid-session activation. The
residue's published log therefore remains readable but shared, which is what task 8.6
expects for that launch mode.

*Still to measure (8.6b):* reopen the project from Unity Hub without activating, and
confirm the surviving stale publication does not impersonate a controlled session —
requires the operator, and doubles as task 1.6 (whether Unity clears
`Temp/UnityPuerExec/` on reopen).

### R3: A domain reload never reads as not-under-control — measured, and it found a real defect (tasks 1.1, 8.9, 4.10)

Measured on the live controlled host by triggering a script reload from inside the
Editor (`exec` of `EditorUtility.RequestScriptReload()`) and polling the session-state
decision densely across the reload window (`.tmp/probe_reload_window.py`).

The first run **caught a defect the transient-gap rule was written to prevent.** The
window produced one `(not_under_control, health=ready)` reading. Timeline, confirmed
by the session marker changing (`a312e191` → `6f9ad27e`): when the service restarts
across a reload it mints a fresh marker and rewrites the publication, and a probe
taken between the new service answering `/health` and the new publication landing on
disk compares the *old* published marker against the *new* health marker — a
transient `mismatched`. The first implementation returned `not_under_control`
immediately on `mismatched`, with no grace retry. That is exactly the "single failed
publication read or probe while the lockfile is held" that task 4.10 forbids.

The fix folds `mismatched` into the same grace retry as `unanswered`: neither is a
conclusion on its own while the lockfile is held, the loop re-reads the publication
and re-probes (which self-heals once the two agree), and only past the window does
the published process's liveness decide `controlled` vs `not_under_control`. The
re-run showed only `controlled` across the window (three `ready`, one `health=None`
at the restart instant covered by the live pid), marker `6f9ad27e` → `785d840e`, zero
`not_under_control`.

This is why the CONTROLLED-with-reload path needed a real Editor and not only unit
tests: the defect lived in the millisecond gap between two files agreeing, which a
mock that returns a consistent pair never exercises. A unit test now pins the rule,
but the reason it exists is this measurement.

### R2: `OpenProject` can relaunch with arguments — confirmed, and it grants isolation too (task 1.5)

Measured on the validation host with a throwaway Editor probe. The
`EditorApplication.OpenProject(string, params string[])` overload exists, compiles,
and the relaunched process reported:

```
Q1 -logFile honoured?          True
     bound log = <project>/Temp/UnityPuerExec/probe_1_5.log
Q2 activation switch present?  True
Q3 endpoint published?         True
full command line: Unity.exe -logFile <...>/probe_1_5.log -unityPuerExecControl
                             -projectpath <project> -force-gles30 -force-gles30
```

Unity places the supplied arguments ahead of the `-projectpath` it appends itself,
and does not override `-logFile`.

*Consequence that changes the shape of D4.* The escape hatch was expected to be a
one-way door: a mid-session activation grants control but can never grant isolation,
because the log is bound at process start. That is still true of the *current*
process — but a restart is a new process, and this result shows a restart can be
driven from inside the Editor with both `-logFile` and the activation switch. So
"Restart with CLI Control" is not a convenience wrapper around half a capability; it
is a one-click return to the fully controlled state, isolation included, from an
Editor a human opened from Hub.

Task 3.5 therefore ships. The session-scoped activation action remains, because a
restart is disruptive when an operator has unsaved work and only needs control.

### R1: Publication atomicity — confirmed, with a contention caveat (task 1.3)

Measured on the Windows validation machine with a writer replacing the target and
four reader threads reading it concurrently (`.tmp/probe_atomic_replace*.py`, three
runs: a ~10 000 reads/s stress run and two runs nearer the real cadence).

**A reader never observes a truncated record.** Across roughly 63 000 concurrent
reads, zero partial or malformed records were seen. A replacing rename
(`MoveFileEx` with `MOVEFILE_REPLACE_EXISTING`, which is what `os.replace` and
.NET's `File.Replace` both issue) gives a reader either the previous complete
content or the new complete content. This settles the spec scenario "A partially
written publication is never observed", and it holds regardless of which side
issues the rename, so the C# writer inherits it — provided it uses a replacing
rename and never truncates the published file in place.

**The rename itself is not contention-free.** A reader holding the destination
open denies the replace with `ERROR_ACCESS_DENIED` (5), because the usual read
open shares read access but not delete access. Readers do not deny each other, so
this is one-directional: reads stay clean while publishes occasionally fail. At a
synthetic 400 reads/s it cost roughly 1% of publishes even with a 400 ms retry
budget; at the real cadence — publish on bind and on port change, read once per
CLI command — it is not expected to be observable.

*Consequences for the implementation.*

- The Editor writes a sibling temp file and replaces the target. Where the target
  does not yet exist, a plain move is used, since `File.Replace` requires it.
- The publish retries with a short backoff and treats exhaustion as non-fatal: the
  previously published record is still valid, and the next publish trigger retries.
  A failed publish must never fail the Editor's startup.
- The CLI retries a denied read briefly. A read it still cannot complete falls
  under the D2 transient-gap rule — momentarily unreadable is not "did not opt in".

## Open Questions

- **A booting Editor is indistinguishable from one that did not opt in — unresolved.**
  Found while applying, and not yet answered. Unity takes the project lockfile early
  in startup but does not publish until its service binds, so for the 30–60 s a cold
  Editor takes to come up, the state is `held + absent` — the same reading as a
  Hub-launched Editor that will never opt in. The command that performs the launch is
  unaffected, because it goes straight to its own readiness wait without
  re-classifying. A *second* command issued during that window is not: it classifies,
  waits out the grace window, and refuses with `editor_not_under_cli_control`. The
  previous behaviour was to wait, via `_has_recoverable_editor_signal`.

  This is a regression the D2 table does not cover, and the risks section already
  named its shape ("a recovery path depends on artifact state in a way the table does
  not cover"). Candidate discriminators, none yet chosen:

  - The project-private launch log exists and is still growing — the activity tracker
    already measures exactly this, and it is evidence about *this* project.
  - The launch claim, if its lifetime were extended from "until the launching command
    returns" to "until the launched Editor publishes". This changes launch-coordination
    semantics and needs its own thought.
  - Lockfile freshness (`PROJECT_RECOVERY_WINDOW_SECONDS`), which is already computed —
    but a Hub-launched Editor has an equally fresh lockfile, so on its own it only
    trades a false refusal for a false wait.

  The regression test that pins this is
  `test_ensure_session_ready_recovers_when_launched_process_exits_cleanly_before_ready`.

- **`EditorApplication.OpenProject` with arguments.** A second menu action, "Restart with CLI Control", could relaunch the Editor with `-logFile` and the activation switch, turning the escape hatch into a one-click return to the controlled state. This is **unverified** in this repository and Unity version. If it does not work as assumed, only the session-scoped activation action ships.
- ~~**Publication lifecycle at the edges.**~~ *Resolved (task 1.4/1.6).* Both edges
  are now measured. The reload edge is covered by R3: the publication is retained
  across a domain reload and a compiling Editor never reads as not-opted-in. The
  quit edge is moot in the direction that mattered: R5/1.6 showed Unity clears
  `Temp/UnityPuerExec/` on reopen and R4/8.6a showed it survives a kill, so on a
  clean exit the publication is removed by Unity's own `Temp/` teardown whether or
  not the `EditorApplication.quitting` hook also deletes it — the two are
  indistinguishable and the D2 residue row absorbs any clean-exit residue that does
  briefly survive. No separate confirmation of the hook is load-bearing.

## Risks / Trade-offs

- **Large blast radius in `unity_session.py`.** ~85 references to `session_data`/`read_session_artifact` are concentrated there, and the artifact currently participates in recovery signalling and launch-conflict detection, not just addressing. → The D2 state table is intended to replace those branches wholesale rather than field-by-field; the risk is that a recovery path depends on artifact state in a way the table does not cover. Mitigated by keeping the existing real-host recovery cases as the acceptance bar.
- **A human who keeps a project open in Unity Hub loses the current silent-attach behavior.** → Intended and marked BREAKING. That behavior only appeared to work when exactly one Editor was open; when it was not, it produced the misattributed failure this change's evidence comes from. The refusal carries the two ways forward.
- **Clicking a menu item on every Editor start is friction.** → Accepted, and the friction is the point (D4). The low-friction path is letting the CLI launch the Editor, which is also the only path that yields isolation.
- **Batch-mode callers must now pass the switch to get a control service.** → Intended; it replaces an implicit suppression with a caller decision, and the batch-mode suppression test becomes a test of the default rather than of a special case.
- **`endpoint.json` could be mistaken for the removed `session.json`.** → D1 states the distinction explicitly; the durable spec should carry it so a later reader does not "restore" CLI-side writing as a convenience.
- **The lockfile ruling is Windows-shaped.** `_project_lockfile_is_held` decides via `msvcrt.locking`, and D2/D5 promote that probe to the sole arbiter of "stopped". → Acceptable while real-host validation is Windows-only; the durable spec states the rule as "the project lockfile is held", so a future platform port replaces the probe, not the contract.
