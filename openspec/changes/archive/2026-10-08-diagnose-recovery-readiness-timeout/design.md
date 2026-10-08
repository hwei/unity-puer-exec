## Context

Observed on the validation host while running the real-host suite on a machine with
several unrelated Unity Editors open. The requested project's Editor was launched by the
CLI, published its endpoint, and logged readiness — but the CLI's recovery wait held a
candidate and never matched the live endpoint:

```
wait-for-exec -> status "running" for the full 240s budget
session.owner = published_endpoint_recovery
session.base_url = http://127.0.0.1:55234
session.unity_pid = 87640
recent_editor_log_lines:
  "[UnityPuerExec] Port 55233 unavailable: ..."
  "[UnityPuerExec] Published endpoint at .../endpoint.json"
  "[UnityPuerExec] Ready on port 55234"
last_health_error = "no endpoint matched the target project yet"
idle_seconds = 20.126
```

The Editor is provably healthy (its own log says so). So the failure is in resolution, not
in the Editor. `diagnose-exec-endpoint-misroute` already hardened *initial* discovery to
range-scan with health-identity matching. The residual case is a wait that has already
picked a candidate `base_url` and must notice when that candidate is stale while a ready,
project-matched endpoint exists elsewhere in the range.

## Goals / Non-Goals

**Goals:**

- Identify the resolution step that failed to claim the ready endpoint and why.
- Make a recovery wait converge on the ready, project-matched endpoint.
- Keep the "never claim another project's endpoint" guarantee and the bounded wait.

**Non-Goals:**

- The automatic-refresh request-recovery defect (that is
  `diagnose-exec-missing-after-auto-refresh`).
- The CLI empty-response parse defect (that is `diagnose-empty-response-parse-error`).
- Changing the launch path, the log-isolation model, or the control-port binding rules.

## Investigation record

### Site map (task 1.1)

Read end to end: `ensure_session_ready` / `_ensure_session_ready_unguarded` (candidate
selection), the four readiness waits it drives, `unity_session_wait.wait_for_session` (the
recovery wait loop), `unity_wait`'s two resolvers, and the `wait-for-exec` resolution in
`unity_puer_exec_runtime.py`.

| # | Site | What it does with a candidate | Re-runs range-scan discovery? |
|---|---|---|---|
| 1 | `unity_session._make_published_endpoint_resolver` | Reads `Temp/UnityPuerExec/endpoint.json`, probes the published `base_url`, requires the live `/health` `session_marker` to equal the publication's. Returns `None` otherwise. **Wired into all four readiness waits** (`unity_session.py` 808, 919, 969, 1042). | **No** — this is the defect. |
| 2 | `unity_session_wait.wait_for_session` | The wait loop. Calls `endpoint_resolver()` once per tick; on `None` it sets `skip_probe` and records `"no endpoint matched the target project yet"` (`unity_session_wait.py:195`). | No — it delegates entirely to the resolver and never scans itself. |
| 3 | `unity_session._make_recovery_endpoint_resolver` | Stateful resolver that *does* range-scan with health-identity matching (`_scan_for_project_endpoint_any_status`), locking onto the first project-matched endpoint. | Yes — but it is **dead code**: it was wired into the four readiness waits before commit `4d9ed3c` ("let the Editor publish its own endpoint") replaced it everywhere. No product call site remains. |
| 4 | `unity_session.wait_until_recovered` | Builds a recovery wait with **no** `endpoint_resolver` at all, so the loop probes `session.base_url` directly. | No. Not on the readiness path that failed; guarded by the misroute regression. |
| 5 | `unity_session._raise_editor_not_under_control` | The error path. Scans via `discover_project_endpoint`, but only to enrich a refusal it raises unconditionally. | Yes, but the scan cannot change the outcome. |
| 6 | `unity_puer_exec_runtime._ensure_project_session_ready_after_refresh` | Delegates to `ensure_session_ready` — identical path. | No. |
| 7 | `unity_puer_exec_runtime._settle_base_url_after_refresh` | Re-probes one caller-supplied `base_url` for a compile cycle. | No — by design (its own change). |
| 8 | `unity_puer_exec_runtime._run_wait_for_exec_impl` | Catches `UnityStalledError` / `UnityNotReadyError` from site 1's wait and, with a pending exec, returns `EXIT_RUNNING`. **This is where the non-terminal `running` is produced.** | No. |

So: site 2 emits the text, **site 1 is the site that drops the endpoint** — it holds one
candidate and returns `None` instead of re-running range-scan discovery — and site 3 is the
already-written scan that is no longer reachable.

### Reproduction (task 1.2)

`.tmp/diag-recovery-readiness-probe.py` drives the real path
(`ensure_session_ready` → `classify_session_state` → `wait_ready_with_activity` →
`wait_for_session` → the real `_make_published_endpoint_resolver`) with mocked health
transitions and a fake clock, so it is deterministic and instant. Single instance
throughout: one Editor pid, one publication, no second project's Editor.

| Case | Mock | Today's outcome | Claims the ready endpoint? |
|---|---|---|---|
| A — stale candidate, ready on a later port | publication pins 55233 (live pid, port answers nothing); project ready on 55234 | `UnityNotReadyError` after the full budget, `owner=published_endpoint_recovery`, `base_url=55233`, `last_health_error="no endpoint matched the target project yet"` | **No** |
| A2 — candidate port reclaimed by another project | as A, but 55233 now answers with a *different* project's ready endpoint | identical failure | **No** |
| B — identity mismatch on the pinned port | publication pins 55234 but with the previous `session_marker`; the live service answers 55234 with the new one | `UnityNotReadyError` after the full budget, `owner=published_endpoint_recovery`, `base_url=55234`, `unity_pid=87640`, `last_health_error="no endpoint matched the target project yet"` | **No** |
| C — control, matching marker | publication pins 55234 and the marker matches | returns a `published_endpoint` session | Yes |

Case B reproduces the real-host diagnostics field for field. Case C proves the probe is not
vacuous. Decision 1's two states are therefore *both* real, *both* reachable, and *both*
terminal for the wait; they are separated only in how the candidate went bad, not in the
fix they need — one re-scan covers both.

### Are the environment preconditions load-bearing? (task 1.3)

**No — the multi-instance condition is incidental to the defect, and a precondition only of
the observed staging.**

- Every failing case above reproduces with a single Editor and no competing host state.
  Nothing in cases A, A2, or B consults another project's Editor, and case A does not even
  have anything else listening.
- What the multi-instance host supplied was the *occasion* for a stale publication, not the
  cause of the wait's inability to recover from one. The recorded failure shows eight
  Unity processes and the pre-launch boundary evidence
  (`endpoint_publication_exists: True`, `project_lockfile_held: False`) naming a **residue**
  publication on port 55234 for a dead pid `27016`, while the freshly launched Editor bound
  55234 again and republished. Port contention on 55231–55233 is what makes a project roll
  over the preferred port and what makes a republish double-write a live file; neither is
  required for the resolution gap to exist.
- Therefore a fix that only works under contention would be the wrong fix, and a unit
  reproduction that mocks the transition is the honest way to pin it.

### Decision 4: The scan range covers every port the service can bind

The requirement says the scan runs "across the bounded control-port range that the Unity
control service binds within". The two sides disagreed: `UnityPuerExecServer` binds
`for (port = PreferredPort; port < PreferredPort + MaxPortAttempts; port++)` with
`PreferredPort = 55231` and `MaxPortAttempts = 20`, i.e. 55231–**55250 inclusive**, while
`direct_exec_client` set `CONTROL_PORT_END = 55250` **exclusive**, stopping one short at
55249. The real-host harness already mirrored the Editor (`CONTROL_PORT_ATTEMPTS = 20`), so
the CLI constant was the odd one out.

This was latent while the readiness path never scanned, and becomes load-bearing the moment
Decision 2's fallback does. `CONTROL_PORT_END` is now `55251`, and the equality is pinned
against the package source by `test_cli_control_port_range_covers_every_port_the_service_can_bind`
(reading `PreferredPort` / `MaxPortAttempts` out of `UnityPuerExecServer.cs`), with
`test_discover_project_endpoint_reaches_the_last_port_the_service_binds` covering the
behaviour. No new normative text is needed: the requirement already promised full coverage
of the service's bind range; the code now matches it.

### Follow-up candidates found while mapping (disposition)

Two findings were outside this defect's fix. Both were surfaced for a human disposition
rather than absorbed into this diff (`apply-closeout-review`), and both were then approved
for promotion into a single follow-up change, `harden-control-port-rollover-validation`:

1. **`validation-gap` — the real-host rollover cases skip under exactly the contention they
   need.** `test_control_port_rolls_over_when_preferred_port_occupied_against_real_host` and
   `test_exec_discovers_rolled_over_control_port_against_real_host` both
   `skipTest("preferred control port ... is held by an unrelated service")` when another
   project's Editor holds 55231 — which is the precondition its durable scenario names. On a
   host with several Editors open the rollover/discovery paths are therefore not exercised by
   the suite, and this change's real-host confirmation came from a purpose-built probe
   (`validation-evidence.md`) instead. **Promoted.**
2. **`tooling-improvement` — `_scan_for_project_endpoint_any_status` is named for a
   capability it cannot have.** Only a `ready` payload carries `project_path`, so "any
   status" overstates it; its docstring is corrected here, the name is not (renaming would
   churn an existing test). That test,
   `test_scan_any_status_finds_rolled_over_cold_start_editor`, also asserts against a
   `compiling` payload that *does* carry `project_path`, which the bridge never emits — the
   ordering and identity-matching it checks are real, its premise is not. **Promoted** as a
   ride-along task in the same follow-up change.

## Decisions

### Decision 1: Confirmed root cause — the readiness waits stopped range-scanning

The four project-scoped readiness waits resolve their endpoint through a resolver that is
**pinned to the single `endpoint.json` publication** and admits that candidate only when the
live `/health` `session_marker` equals the publication's marker. When the publication is
absent, unreachable, or carries a marker the live service has already replaced, the resolver
returns `None`; the wait sets `skip_probe`, records `no endpoint matched the target project
yet`, and repeats — for the entire budget, without ever re-running range-scan discovery. The
`running` (exit 10) status is then produced by `wait-for-exec`'s pending-exec branch.

Observed sequence, reconstructed from the recorded payload:

1. A residue publication for the project named port 55234 and a dead pid. The boundary
   confirmed `project_lockfile_held: False` with `endpoint_publication_exists: True`.
2. The CLI launched the project. On a host where 55231–55233 are held by unrelated Editors,
   the new Editor bound 55234 — the same port the residue named — and republished.
3. The wait's candidate was therefore the publication, and its `base_url` and `unity_pid`
   agreed with the live Editor (`55234`, `87640`); only the live identity the resolver
   compares (`session_marker`) could not be confirmed, so `confirm_publication` returned
   `unanswered`/`mismatched`. Past the 2s restart grace with a live published pid,
   `classify_session_state` resolves to `CONTROLLED` with **no health payload** — which is
   exactly the recorded `owner=published_endpoint_recovery` shape.
4. The recovery wait then re-read the same unconfirmable publication every tick and returned
   `None` every tick. The Editor logged `Ready on port 55234`, wrote nothing further, and 20s
   later the activity stall fired — `idle_seconds: 20.126` against the 20s
   `DEFAULT_ACTIVITY_TIMEOUT_SECONDS`.

Rejected alternatives:

- **"The publication is never rewritten, so the wait follows a stale port."** Rejected as
  the whole story: the recorded `session.unity_pid` equals the *live* Editor's pid, and the
  recorded `base_url` equals the port its own log calls `Ready on`. The publication was read
  successfully and named the live port; what failed was confirming it. Case A/A2 show the
  stale-port variant is reachable too, which is why the fix must not be marker-specific.
- **"`wait_for_session` falls back to probing `session.base_url` and misroutes."** Rejected:
  the loop deliberately suppresses that fallback (`skip_probe`) to protect the misroute
  guarantee, which is why no probe is recorded and why the wait cannot self-heal.
- **"The Editor's service never bound / the endpoint is genuinely absent."** Rejected: the
  Editor's log records `Published endpoint` and `Ready on port 55234`, and case C shows a
  matching marker resolves today. Decision 2 in the original draft — "the fix converges, it
  does not widen" — is what the evidence supports.

Evidence: the reproduction table above, plus the recorded failure payload in
`.tmp/after5.log` and the archived analysis in
`openspec/changes/archive/2026-09-21-reuse-real-host-editor-across-suite/validation-evidence.md`.

### Decision 2: The fix converges, it does not widen

The existing requirement already promises range-scan discovery at "recovery waiting" and
"the wait that follows a cold-start launch". The code violates that, so the fix restores the
promise and the delta is only an explicit scenario. Concretely: keep the publication as the
one-probe fast path, and when it cannot be confirmed, fall back to the range scan that
already exists (identity by `project_path`, never by port or pid). A ready endpoint owned by
another project stays unclaimable (proposal 2.3).

Identity-strictness is what makes this safe: only a `ready` payload carries `project_path`
(`compiling` and `not_available` carry the marker and pid but no project path), so the
fallback can only ever claim an endpoint that identifies itself as the requested project. It
therefore converges once the project's Editor reports ready — which is the case the
requirement names — while a pre-ready endpoint is covered by the publication fast path
instead.

### Decision 3: Bounded wait survives

A wait that can no longer find any recoverable signal must still terminate with its
terminal outcome; convergence must not become an unbounded poll (task 2.4). The wait loop's
deadline, its 20s activity stall, and the launcher-exit check are all unchanged, and the
fallback only runs on ticks where the publication fast path already failed, so a genuine
"no endpoint will ever appear" case still surfaces its terminal outcome within the budget.

## Risks / Trade-offs

**[The defect is only reproducible under multi-instance contention]** → Resolved by
investigation: it is not. Every case reproduces single-instance (task 1.3 above). The
multi-instance host is the occasion, not the cause, and the regression tests therefore mock
the transition rather than the contention.

**[A re-scan on every wait tick could be expensive]** → The publication fast path is kept and
costs one probe per tick; the sweep only runs when that path has already failed, and once
the scan matches it re-probes the locked port only. The bounded-wait check (task 2.4) covers
the terminal case, and review covers the fast path.

**[A fallback could claim an endpoint the old resolver would have refused]** → The fallback
compares `project_path`, the same identity the misroute guards use, and never compares ports
or pids for ownership. Task 2.3 re-runs the endpoint-identity and misroute coverage against
`_make_recovery_endpoint_resolver`'s existing guarantees.
