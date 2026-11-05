# Design

## Context

See `proposal.md` — Why. The mechanics that matter here:

- `UnityPuerExecImportChangeTracker.Decide()` is the only refresh decision. It walks the
  watched roots, compares each compile-triggering file's mtime against
  `settledImportUtcTicks`, and returns `compile_triggering_change` when anything is newer.
- `settledImportUtcTicks` has exactly one writer: `OnCompilationCompleted()`, called from
  `UnityPuerExecServer.OnCompilationFinished` and `OnAfterAssemblyReload`. `tests/test_refresh_change_signal.py`
  asserts that single-writer property mechanically, and the real-host case
  `test_exec_and_refresh_do_not_advance_settled_timestamp` asserts that a no-compile
  `AssetDatabase.Refresh()` leaves it alone.
- `UnityPuerExecServer.EvaluateRefreshAsync()` runs the decision and the dispatch on the main
  thread, and both `/exec` and `/refresh` go through it. The server never waits for the
  resulting compilation; the CLI settles the cycle and re-submits.
- The CLI's budgets are what turn a permanent pending state into a multi-minute loop:
  `_play_pre_settle` re-asks `/refresh` every second until `2 × 180 s`, and the exec loop
  permits one resubmit before reporting the non-terminal `refreshing` phase.
- `GetPendingState()` feeds `/health`, which feeds `wait-for-compile`'s `compile_blocked`
  decision and `get-blocker-state`. It calls the same scan as `Decide()`.

Upstream findings that remain true: `2026-09-21-refresh-on-change` established that mtime
versus the settled timestamp is the whole signal, and that importing a file does not change
its mtime. `2026-09-21-diagnose-exec-missing-after-auto-refresh` established that a refresh
is a non-terminal phase of an accepted request that the CLI settles and re-submits, with a
compile-scale budget of its own. Neither anticipated a refresh that Unity resolves without
compiling: the requirement "Settled-import timestamp advances only on Unity completion
signals" silently assumes every pending change eventually produces one. Issue #3 is that
assumption failing, and the gap this design closes is on the detection side, not the
timestamp side.

## Goals / Non-Goals

**Goals:**

- A content-identical rewrite of a compile-triggering file stops being a triggering change
  within a bounded window, so `play` completes in a single CLI invocation and `exec` stops
  looping for the life of the Editor session.
- The fix is host-side and caller-agnostic: an older CLI, a `--base-url` caller, and a
  `wait-for-compile` caller all benefit without changes.
- The settled-import timestamp keeps its single writer and its "only on Unity completion
  signals" rule, so every existing invariant test and real-host case stays meaningful.
- A suppressed decision stays observable: an operator reading the refresh block can tell
  "nothing was newer" from "newer, but already handed to Unity".
- Suppression never hides a build Unity has not finished producing. A candidate stays
  triggering while Unity may still compile it, so a failing build is still reported as one.

**Non-Goals:**

- No content hashing of unflagged trees. Detection still costs enumeration and stat when
  nothing is flagged.
- No new endpoint, no CLI-side acknowledgement, no protocol removal.
- No change to play-mode suppression, dot-directory exclusion, or the extension filter.
- No attempt to make `AssetDatabase.Refresh()` force a compilation. A forced recompile would
  pay a full compile plus domain reload for a file whose content Unity already has.

## Decisions

### D1. Filter the candidate set by content instead of advancing the timestamp on "no compile observed"

Issue #3 offers two directions. The first — let the host advance the settled timestamp when a
dispatched refresh is followed by no compilation — was rejected:

- Advancing the timestamp is global. It drops every candidate older than the dispatch
  instant, including one the scan had not yet seen, whereas the failure being fixed concerns
  one file's content.
- It needs the same bounded observation window D7 ends up needing, but spends it on a state
  change that cannot be narrowed afterwards.
- It amends the requirement `tests/test_refresh_change_signal.py` and the real-host case
  `test_exec_and_refresh_do_not_advance_settled_timestamp` exist to guard.

A content filter is narrow (it can only drop a path whose exact content was already handed to
a successful dispatch) and keeps the timestamp invariant intact. It is not, as first drafted,
free of timing: D7 records what the real-host suite found when it was.

### D7. Suppression waits for Unity's chance to compile

The first implementation suppressed on a content match alone, with no age and no activity
gate. `RefreshOnChangeRealHostTests` passed; `PlayModeCompileBlockRealHostTests.
test_play_aborts_on_a_compile_error_without_entering_play_mode` failed with exit `10`
(`running`, `phase: play_mode`, `play_state: edit`) instead of `23` (`unity_compile_error`).

The sequence: `play` wrote a deliberately broken `.cs`, `/refresh` dispatched and recorded
its content, and the CLI's project-path settle returned before Unity had started the
compilation. The next `/refresh` matched the record, suppressed the only candidate, found no
compile-error snapshot yet — `compilationStarted` clears it — and answered `completed`. The
pre-settle concluded the build was clean and posted the play-mode request into a compile that
had not started, so the Editor stayed in `edit` and the case saw a non-terminal `running`.

The mtime-only signal handled this by accident: with nothing to suppress, every re-ask
re-dispatched and reported the non-terminal refreshing phase until the compile finished and
produced its error snapshot. Suppressing removes that accidental wait, so the wait has to be
stated. Two gates restore it:

- **Bounded age.** A record suppresses only once it is at least `PostRefreshSettleGraceTicks`
  past its dispatch. The value is tied to the caller rather than guessed: it must stay under
  `DEFAULT_COMPILE_APPEAR_TIMEOUT_SECONDS` (10s), the budget a caller spends waiting for a
  compile to appear before concluding `no_compile_observed`. A caller that waits out its own
  appear window and re-asks once therefore always re-asks after the host has acknowledged,
  which is what keeps base-url `exec` and `play` single-invocation.
  `tests/test_refresh_change_signal.py` reads both constants and asserts the ordering, so the
  tie cannot drift silently.
- **Editor activity.** A record suppresses only while the Editor is neither compiling nor
  importing. `EditorApplication`'s flags are main-thread-only and the pending view is
  answered on the listener thread, so the tracker keeps one volatile snapshot sampled by the
  server's update tick before that tick drains the action queue carrying `Decide()`. A
  decision therefore never reads a snapshot older than the tick it runs in.

**First dispatch wins.** A caller that re-asks before the bounded age elapses gets a
triggering decision and re-dispatches the same content. Re-stamping the record on that
re-dispatch would push the age out again and restore the exact loop the ledger exists to end
— `play` polls `/refresh` once a second for up to six minutes. `OnRefreshDispatched` keeps the
existing record when the content hash is unchanged.

Known cost: `exec --project-path` settles through `ensure_session_ready`, which does not wait
for a compile to appear and can return inside the bounded age. Its single permitted resubmit
then lands on a still-triggering decision, so an identical-content rewrite needs a second
invocation — reported as the replayable non-terminal `refreshing` phase, which
`wait-for-exec --request-id` continues. That is a CLI-side settle-budget gap, recorded as a
follow-up candidate rather than absorbed here.

### D2. Key the ledger on content, not on mtime

Recording `(path → mtime)` at dispatch would also break the reported loop, and would cost no
file reads. It was rejected because mtime is the proxy that just proved unfaithful: a tool that
writes identical content twice with two mtimes costs a refresh each time, and a tool that
writes different content under an unchanged mtime (some checkout and archive paths do) is
suppressed as a false negative. A content hash has neither failure. The cost is one read and
hash per already-flagged path per decision, typically 0–3 files.

### D3. Record after a successful dispatch, clear when the timestamp advances

The ledger means "content this Editor session already asked Unity to import, and Unity has
given no completion signal since". Two edges keep that meaning honest:

- Written only when `AssetDatabase.Refresh()` returned without throwing (`settle_outcome:
  "dispatched"`). A failed dispatch records nothing, so the next decision retries.
- Cleared inside `OnCompilationCompleted()`, the timestamp's single writer. Anything Unity has
  now imported is covered by the advanced timestamp, and a stale entry can never survive a
  settle to suppress a later identical-content write that Unity has not seen.

The hashes are computed at decision time, before the dispatch, and carried on the decision
object. Hashing after the dispatch would record content that arrived during the refresh and
suppress a change Unity never saw.

### D4. The ledger is in-memory and does not need to survive a domain reload

Any domain reload fires `afterAssemblyReload`, which advances the settled timestamp past every
mtime the scan could have flagged, so the ledger is moot after a reload. Keeping it in statics
also keeps it out of `SessionState`, where a path-keyed map would grow without bound. The
"no in-memory event state" rule in the detection requirement is about *missed* detections:
losing this record restores the unfiltered candidate, so a reload makes detection more eager,
never less. The requirement text is amended to say exactly that.

### D5. `GetPendingState()` applies the same filter

`/health` and the decision must not disagree. If health reported `pending` for content the next
`/refresh` would suppress, `wait-for-compile` would keep returning `compile_blocked` in play
mode for a change nothing will ever compile, and `get-blocker-state` would name a blocker that
is not one. Both paths therefore share one filter helper; the hash pass is the extra cost on
the health poll, bounded by the flagged-path count.

### D6. Disclose suppression in the existing refresh block as `paths_suppressed`

A decision that suppressed everything reports `triggered: false` with
`skipped_reason: "no_pending_change"` — a value every existing caller already treats as
"proceed", which is why no CLI change is needed. That alone would be indistinguishable from a
tree with nothing newer, so the block gains `paths_suppressed`. It is additive: the CLI copies
the block verbatim into its payloads, `tests/test_real_host_integration.py` asserts the
existing keys with `assertIn`, and no consumer validates the key set. This is where the
"Refresh decision diagnostics remain available for precision measurement" requirement is
honoured — the false-positive rate of the mtime signal becomes readable from an ordinary
transcript.

## Risks / Trade-offs

- **[Suppression hides a build Unity has not finished producing]** → Found, not hypothetical:
  it failed `test_play_aborts_on_a_compile_error_without_entering_play_mode` during apply. D7's
  bounded age and editor-activity gates close it, and that case is the regression proof.
- **[The bounded age is a chosen constant]** → It is bounded by the caller's own compile-appear
  budget rather than picked in isolation, and `tests/test_refresh_change_signal.py` reads both
  constants and asserts the ordering. Too long only costs latency in the identical-content
  case; too short is what D7's gates now prevent.
- **[Unity silently ignored a dispatched refresh, so the recorded content was never imported]**
  → The record is written only after a successful dispatch, is cleared on every settle, and is
  keyed on exact content: the next write to that file, whatever it contains, re-triggers. The
  residual exposure is one file held at one content state, which is the same exposure the
  timestamp already has for any change Unity declines to compile.
- **[A content read per flagged path per decision adds I/O to the hot poll path]** → Only
  flagged paths are read, and only when at least one exists; a settled tree reads nothing. The
  real-host case for "no candidate costs no content read" pins that.
- **[Concurrent decisions on the listener thread and the main thread]** → The scan and the
  content read run outside the lock; the ledger and the activity snapshot are read under the
  existing `Gate` or as a volatile.
- **[A caller depends on a no-compile refresh looping]** → No such contract exists. The loop is
  the bug; the CLI's own budgets treat it as exhaustion.

## Migration Plan

Host-only. Deploy with the next package version; no state to migrate, no CLI pairing
requirement, and an older CLI against a newer host simply stops looping. Rollback is removing
the filter, which restores the previous behaviour exactly because the ledger never writes the
settled timestamp.
