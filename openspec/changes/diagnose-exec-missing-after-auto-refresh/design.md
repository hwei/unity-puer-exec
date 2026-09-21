## Context

The failure is deterministic on the validation host and was isolated while applying
`reuse-real-host-editor-across-suite`; it reproduces on both the old per-case-relaunch
harness and the new shared-host harness, so it is pre-existing and independent of that
change. The trigger is the interaction between two shipped behaviors:

1. The import-change tracker notices a compile-triggering write and the CLI's automatic
   refresh settles the resulting compile from the caller's `exec`.
2. That settle is given too small a budget to complete (see Decision 1), so `exec` returns
the refreshing phase without ever resubmitting -- and the server never accepted the job it
was refreshing for, so the request is not recoverable from either side. The domain reload
is not what loses the request; the request was never recorded.

Observed sequence (base-url mode, first case after a cold launch):

```
exec --wait-timeout-ms 1000      (the probe starts an automatic refresh)
  server: triggered=true reason=compile_triggering_change
  -> CLI settles the compile cycle (_settle_base_url_after_refresh) with a 1.0 s window
  -> settle times out; CLI returns EXIT_RUNNING phase=refreshing WITHOUT resubmitting
  -> the job was never accepted, so no record exists server-side either
wait-for-exec --request-id R
  -> exit 13, status=missing, "no recoverable record exists for request_id"
     log_range={start:1690261,end:1690261}
```

The `log_range.start = 1690261` that looked like the strongest lead is refuted. It is
not an artifact field and not a pre-reload offset: it is the CLI-injected observation range
(`_apply_log_range_and_brief_sequence`), i.e. the byte size of the resolved Editor.log at
response time, captured twice microseconds apart, which is why start and end are equal and
why the same number recurs on this machine. See Decision 1.

## Goals / Non-Goals

**Goals:**

- Identify the single owning call site for the loss of recoverability across the refresh
  domain reload, with evidence, not inference.
- Restore the contract that the terminal response carries the script result.
- Keep genuinely expired or malformed artifacts non-recoverable `missing` (do not silence
  the status wholesale).

**Non-Goals:**

- Redesigning the pending-exec artifact lifecycle.
- Changing the non-terminal refresh contract, the code-only refresh boundary, or the
  removed `--refresh-before-exec` behavior.
- Explaining the separately-observed intermittent flakes (launch-recovery endpoint
  resolution, CLI empty-response JSON parse). Those are recorded as follow-up candidates,
  not folded into this change.

## Decisions

### Decision 1: Confirmed owner is the client-side settle budget, not artifact durability

**Confirmed root cause.** `_post_refresh_ready_timeout_seconds`
(`cli/python/unity_puer_exec_runtime.py:890`) derives the automatic-refresh settle budget
from `args.wait_timeout_ms`:

```python
return max(float(args.wait_timeout_ms) / 1000.0, 0.001)
```

That value is the compile-cycle settle budget consumed by `_settle_base_url_after_refresh`
(`:1014` -> `wait_for_compile_cycle(..., settle_timeout_seconds=...)`) and the post-refresh
readiness budget consumed by `_ensure_project_session_ready_after_refresh` (`:894`).
`--wait-timeout-ms` bounds one HTTP wait for an **already-accepted** job; it does not bound
a compile plus the domain reload that ends it. The failing real-host case passes
`WAIT_TIMEOUT_MS = 1000` (`tests/test_real_host_integration.py:36`), so the settle window is
**1.0 s**. No compile+reload meets it, so `wait_for_compile_cycle` returns
`COMPILE_OUTCOME_TIMEOUT`, `_settle_after_automatic_refresh` returns `None`, and
`_run_exec_impl` takes the non-terminal bail-out at `:1332`:

```python
if settled is None or refresh_attempts >= 1:
    ... return EXIT_RUNNING, emit_payload(payload), ""      # no resubmit
```

`exec` therefore returns `running`/`refreshing` **without resubmitting**.

**Why that becomes a non-recoverable `missing`.** The server returns the
refreshing phase *before* `TryAcceptExecRequest`
(`packages/com.txcombo.unity-puer-exec/Editor/UnityPuerExecServer.cs:659` vs `:684`), so the
job was never accepted and `Requests` never held the `request_id` -- by construction, with
or without a reload. In base-url mode the CLI writes no client-side record to fall back on:
every pending-artifact read/write is guarded by `selector == "project_path"`, and
`_run_wait_for_exec_impl` sets `pending = None` for base-url (`:1411-1413`), so
`wait-for-exec --base-url --request-id R` is a pure server lookup that answers
`missing` (`UnityPuerExecServer.cs:883`). `_running_or_timed_out_response` (`:1110`) never
resubmits `missing`, so the caller gets exit 13 with no script result.

**Rejected alternative: the pending artifact is lost or invalidated by the reload.**
Refuted three ways.

1. In base-url mode there is no pending artifact at all -- every read/write is guarded by
   `selector == "project_path"`, and there is no project path to key one on. Nothing can be
   lost or invalidated because nothing was written.
2. `log_range` is CLI-injected observation metadata, not artifact content. Reproducing the
   failure locally emits the identical `log_range={start: 1690261, end: 1690261}` on this
   machine because it is the resolved Editor.log size, not a replayed offset.
3. `PENDING_EXEC_RETENTION_MS` is 24 h (`unity_session_common.py:58`); a domain reload
   cannot expire an artifact. Expiry also deletes-and-reports, which is the behavior
   `implement-pending-exec-artifact-lifecycle` intended, and the observed payload carries no
   artifact-derived field at all.

**Evidence that the budget alone is the trigger.** The same class already carries the
counterexample for the same code path: `_exec_script` uses
`REFRESH_WAIT_TIMEOUT_MS = 300_000` with the comment that "an exec that may trigger an
automatic refresh has to give the CLI's internal settle+resubmit loop enough budget", and
those cases pass. Driving the reproduction at both budgets against unchanged code:

```
wait_timeout_ms=1000    exit=10  invokes=1 status=running    phase=refreshing log_range={'start': 1690261, 'end': 1690261}
wait_timeout_ms=300000  exit=0   invokes=2 status=completed  phase=None       log_range={'start': 1690261, 'end': 1690261}
```

Same request, same cycle length, same session-marker path; only the budget differs. The
1.0 s case is the deterministic real-host failure.

**Invariant that changed.** "The budget for settling the compile cycle an automatic refresh
started is the caller's per-request `--wait-timeout-ms`" becomes "it is the compile-scale
readiness budget (`DEFAULT_READY_TIMEOUT_SECONDS`), the same budget
`wait-for-compile --settle-timeout-seconds` gives the identical cycle". The `missing`
classification itself is untouched and remains correct.

### Decision 2: Preserve `missing` for real expiry, fix only the reload case

`implement-pending-exec-artifact-lifecycle` deliberately treats expired/malformed
artifacts as non-recoverable `missing`. That contract stays. The fix must make the
refresh-triggered reload distinguishable from genuine expiry, so the change does not
degrade the caller-visible signal into a blanket resubmit.

### Decision 3: Provisional spec delta confirmed as-is

Task 1.3 showed the defect is the CLI failing to perform the settle the requirement already
mandates, not a gap in what the requirement demands. The existing normative text ("the CLI
settles on the compile cycle before running the caller's script", "the terminal response
carries the script result") already covers the fix, so the delta is confirmed as written:
one explicit scenario naming the reload case, no change to the normative text.

## Risks / Trade-offs

**[Fixing it by resubmitting could double-execute a script with side effects]** -> Resolved
by the confirmed root cause: the server returns the refreshing phase *before*
`TryAcceptExecRequest`, so a request that lost its settle never ran and the resubmit is the
first execution. The preserved invariant is "the resubmit carries the same `request_id` and
only ever follows a phase in which no script ran"; the change does not introduce a resubmit
of a possibly-already-run request.

**[The unit layer may not reproduce a real domain reload]** -> Partly. The reproduction
models the cycle as a clock the health probe reads, which is enough to fail on the budget
arithmetic (`invoke_command.call_count` 1 vs 2) and is specific to the refresh path, not to
a generic timeout. A real reload is still confirmed by the real-host case in task 3.2.
