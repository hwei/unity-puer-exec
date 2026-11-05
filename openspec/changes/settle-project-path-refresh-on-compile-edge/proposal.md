# Proposal

## Why

`fix-unchanged-content-refresh-loop` (archived `2026-11-05`) ended the host-side refresh loop by
suppressing a scan candidate whose content was already handed to a dispatched refresh, gated on a
bounded age of 8 s so suppression cannot outrun a compilation Unity has not started yet. The gate
is sized against the caller: it must stay under `DEFAULT_COMPILE_APPEAR_TIMEOUT_SECONDS` (10 s) so
a caller that waits out its own compile-appear window and re-asks once always re-asks after the
host has acknowledged.

Only one of the two settle paths actually waits that window. A base-url `exec` settles through
`_settle_base_url_after_refresh` → `wait_for_compile_cycle`, which spends the appear window before
concluding `no_compile_observed`. A project-path `exec` settles through
`_ensure_project_session_ready_after_refresh` → `ensure_session_ready`, which waits for `ready` and
rides out a compile already visible, but does not wait for one to *appear*. On a warm host it
returns in ~2 s, inside the bounded age, so its single permitted resubmit lands on a still-triggering
decision and the invocation reports the non-terminal `refreshing` phase. A second invocation
resolves. The host-side gate is correct; the project-path caller just does not give it time to
mature.

## What Changes

- The project-path settle after an automatic refresh waits for the compile edge on the same
  budget the base-url path already uses, so both selectors re-ask after the host's bounded age has
  elapsed.
- An unchanged-content rewrite therefore resolves in one `exec --project-path` invocation instead of
  two, matching base-url `exec` and `play`.
- The compile-scale settle budget stays its own budget and stays distinct from `--wait-timeout-ms`;
  this changes what the project-path settle waits *for*, not how long a caller's request wait is.
- No host change and no protocol change. The bounded age and its tie to the appear window stay
  exactly as `fix-unchanged-content-refresh-loop` landed them.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `formal-cli-contract`: "Automatic refresh is a non-terminal phase of the accepted exec request"
  gains the selector-parity property — the settle that precedes the one permitted resubmit is
  edge-aware in project-path mode as it already is in base-url mode, so a refresh the host resolves
  without compiling converges inside the same invocation.

## Impact

- **CLI**: `cli/python/unity_puer_exec_runtime.py` — `_settle_after_automatic_refresh` and its
  project-path helper `_ensure_project_session_ready_after_refresh`.
- **Host**: none.
- **Tests**: mocked coverage for the project-path settle waiting the appear window before
  resubmitting; a real-host case that an unchanged-content rewrite reaches `completed` in one
  `exec --project-path` invocation.
- **Upstream**: inherits `fix-unchanged-content-refresh-loop`'s finding that the bounded age is
  sized against the caller's appear window, and `2026-09-21-diagnose-exec-missing-after-auto-refresh`'s
  rule that the settle budget is compile-scale and not `--wait-timeout-ms`.
- **Risk**: a project-path `exec` whose refresh starts no compile now spends up to the appear
  window (10 s) before its resubmit, where today it spends ~2 s and returns non-terminal. That is
  the same trade the base-url path already made; the alternative is a second invocation.
