## Why

`exec --base-url` returning `running` now advertises its `wait-for-exec` continuation with a
usable `--base-url` argv, but the other base-url continuation candidates still omit `argv` even
when the response carries every value the invocation needs. A base-url `wait-for-exec` that
returns `running` and the remaining base-url continuations therefore advertise a command
without a runnable invocation, while the same status in project-path mode carries one.

This was recorded as the `product-improvement` follow-up in the closeout of
`2026-10-13-restore-base-url-exec-continuation-guidance`.

## What Changes

- Give every continuation candidate whose target command and originating command both accept
  `--base-url` a `--base-url` argv variant alongside the existing `--project-path` one, selected
  the same way the `("exec", "running")` candidate already is.
- Cover, among others, the `("wait-for-exec", "running")` `wait-for-exec` candidate and the
  remaining selector-reachable candidates across `play`, `pause`, `stop`, `wait-for-compile`,
  `get-compile-errors`, and `get-compile-warnings`.
- Leave unchanged any candidate that names a command accepting only `--project-path`
  (`get-log-briefs`, `get-blocker-state`, `resolve-blocker`) and any candidate whose originating
  response is project-path-only. A base-url completed response still advertises its
  `get-log-briefs` candidate, but that command reads a local log and has no base-url form, so the
  candidate omits `argv` rather than gaining a fabricated flag.
- Reconcile the durable success-path requirement so "complete invocation" is scoped to a selector
  the named command accepts, and a base-url completed response legitimately omits `argv`.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `runtime-guidance`: adds a requirement that a continuation candidate for a command accepting
  both addressing modes carries the selector-appropriate `argv` for the selector the caller used,
  and reconciles the success-path error-sweep requirement so a project-path-only command keeps
  its candidate with no `argv` under `--base-url`.

## Impact

- Affected code: `cli/python/help_surface.py` (selector-variant construction for `GUIDANCE_MATRIX`
  and `WARNING_GUIDANCE_MATRIX` candidates; `_select_argv` selection is unchanged),
  `tests/test_unity_session_cli.py`.
- Affected behavior: base-url continuation candidates gain a runnable `argv` where the
  project-path form already carries one. Project-path argv is unchanged. Project-path-only
  commands keep omitting `argv` in base-url mode.
- Affected validation: unit-only. No real-host requirement, so verifiable in the default suite.
