## Why

`surface-play-mode-compile-block` made an `exec` that runs while the Editor is in play mode
with a pending compile-triggering change disclose a `compile_blocked` object and a
`compile_blocked_by_play_mode` warning. `wait-for-exec` recovers or continues that same
request and returns the same terminal result — but it does not compose the object or apply
the warning.

An agent whose request stays non-terminal and who continues with `wait-for-exec`
(`recover-exec-by-request-id`, the documented path) therefore loses the disclosure the
direct `exec` would have given it, and reads a plain `completed` that silently ran against
stale code. The recovery surface is the one most likely to be used when the first response
was ambiguous, so it is the worst place for the signal to be missing.

There is a second gap behind the first. A response carries exactly one `warning` code, but
two independent conditions can hold at once: `async_result_not_supported` (the entry
function returned a Promise) and `compile_blocked_by_play_mode` (a pending change could not
compile). The runtime currently keeps the async code and attaches the `compile_blocked`
object, and guidance is selected by that single code, so a caller reading `situation` /
`next_steps` never sees the play-mode way out. The object is a reliable machine signal, but
the human-readable guidance is incomplete. The durable `runtime-guidance` requirements that
apply in that response — a situation for the warning, and a situation leading out of play
mode — both have to be satisfied, and one `situation` string has to carry both.

## What Changes

- Apply the same play-mode compile-block composition and warning transition to the
  `wait-for-exec` terminal response path that `exec` already uses.
- Keep the existing precedence rules: a failure status or an existing async warning keeps
  its code, and the `compile_blocked` object is attached in every case.
- When a response carries a `compile_blocked` object, treat it as a CLI-owned guidance
  selector (the same idea as the `version_mismatch` `guard`): merge the play-mode exit
  guidance into the response's own guidance instead of replacing it. The merged `situation`
  covers both conditions, and the merged `next_steps` lead with the play-mode exit steps
  and keep the warning's own steps.
- Do not add a multi-warning response shape. The single `warning` code stays the primary
  contract; the object plus the merged guidance carry the extra condition.
- Reuse the one runtime helper rather than duplicating the composition.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `import-change-refresh`: adds a requirement that a `wait-for-exec` response covering a
  request that hit a play-mode skip with a pending change carries the same
  `compile_blocked` disclosure and warning as the equivalent `exec` response.
- `runtime-guidance`: adds a requirement that a warning response carrying a
  `compile_blocked` object composes guidance from both conditions, instead of selecting the
  async warning's guidance alone.

## Impact

- `cli/python/unity_puer_exec_runtime.py`: the `wait-for-exec` terminal path calls the
  shared play-mode composition helper, and `_attach_guidance` passes the CLI-owned
  `compile_blocked` presence into guidance composition.
- `cli/python/help_surface.py`: guidance composition merges the play-mode exit steps and
  situation with the warning's own, rather than picking one.
- `tests/test_unity_session_cli.py`: unit coverage for the recovered/continued case and for
  the async-warning collision.
- `tests/test_real_host_integration.py`: the play-mode real-host case may assert the
  `wait-for-exec` recovery path.
- No new protocol field; the server already returns `refresh.skipped_reason` and
  `refresh.paths_changed` on the underlying exec.
