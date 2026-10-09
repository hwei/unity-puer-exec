## Context

The play-mode compile-block signal is CLI-composed from the server's exec `refresh` block
(`skipped_reason: "play_mode"` plus `paths_changed`). `exec` composes it in
`_apply_play_mode_compile_block` and applies it before guidance is attached.
`wait-for-exec` reaches a terminal response through its own finalize path, which currently
injects refresh, log range, and guidance but never runs that composition.

## Decisions

### D1. Reuse the single helper at the shared terminal boundary

Rather than a second implementation, `wait-for-exec` calls the same
`_apply_play_mode_compile_block(stdout_text, stderr_text, base_url, args)` immediately
before `_inject_guidance_into_response`, exactly as `exec` does. That keeps the warning
code, the object shape, and the failure/async precedence in one place.

### D2. Only the terminal response is rewritten

A non-terminal `wait-for-exec` (`running` / `refreshing`) has no terminal script result to
annotate, so the helper is applied only where the command is about to return a terminal
response, not on the non-terminal return paths.

### D3. No protocol change

The `wait-for-exec` replay invokes the server's exec path, so the refresh block is already
present on the response. The CLI needs no new field or endpoint.

### D4. `compile_blocked` is a CLI-owned guidance selector, and guidance merges

The collision (`warning: async_result_not_supported` plus a `compile_blocked` object) cannot
be fixed by the warning code alone, because the response has one `situation` and one
`next_steps` while two durable guidance requirements apply. Replacing the single `warning`
code with a `warnings[]` list does not fix it either: the response would still have one
`situation`, so guidance would still have to merge, and the change would break the
established single-code contract that `async_result_not_supported` and `api_updater_declined`
rely on.

Instead, guidance composition treats the presence of a `compile_blocked` object as a
CLI-composed selector, the same idea as the `version_mismatch` `guard` already in
`_attach_guidance`. When it is present:

- the play-mode exit `situation` is merged with the warning's own situation (one string
  covering both conditions);
- the play-mode `next_steps` lead, followed by the warning's own steps (for the async case,
  `wait-for-result-marker`).

The selector reads a CLI-owned envelope field, never a script-authored `result` field, so it
does not violate the durable rule that script-authored result fields never drive candidate
selection. It does extend selection past `(command, status)` for this edge, which is the same
kind of CLI-owned extension the `guard` already is.

### D5. The merge applies wherever the collision can occur

The collision is a property of any warning response carrying `compile_blocked`, so the merge
is implemented in the shared guidance composition, not only in the `wait-for-exec` path. `exec`
benefits from the same fix.
