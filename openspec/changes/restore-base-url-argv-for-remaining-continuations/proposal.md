## Why

`exec --base-url` returning `running` now advertises its `wait-for-exec` continuation with a
usable `--base-url` argv, but the other base-url continuation candidates still omit `argv` even
when the response carries every value the invocation needs. A base-url `wait-for-exec` that
returns `running` and a base-url `exec` that returns `completed` therefore advertise a command
without a runnable invocation, while the same status in project-path mode carries one.

This was recorded as the `product-improvement` follow-up in the closeout of
`2026-10-13-restore-base-url-exec-continuation-guidance`.

## What Changes

- Give each remaining continuation candidate that names a command accepting both selectors a
  `--base-url` argv variant alongside the existing `--project-path` one, selected the same way
  the `("exec", "running")` candidate already is.
- Cover at least the `("wait-for-exec", "running")` `wait-for-exec` candidate and the shared
  `get-log-briefs` completed candidate used by `exec`, `wait-for-exec`, and `wait-for-log-pattern`.
- Leave unchanged any candidate whose command does not accept `--base-url`, and any candidate
  that is selector-agnostic.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `runtime-guidance`: adds a requirement that a continuation candidate for a command accepting
  both addressing modes carries the selector-appropriate `argv` for the selector the caller used.

## Impact

- Affected code: `cli/python/help_surface.py` (`GUIDANCE_MATRIX` entries; `_select_argv` already
  supports the variant shape), `tests/test_unity_session_cli.py`.
- Affected behavior: base-url continuation candidates gain a runnable `argv` where the
  project-path form already carries one. Project-path argv is unchanged.
- Affected validation: unit-only. No real-host requirement, so verifiable in the default suite.
