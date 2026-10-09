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
