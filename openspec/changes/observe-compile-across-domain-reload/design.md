## Context

`wait_for_compile_cycle` observes a compile by seeing `compiling` appear and then `ready`,
or by seeing a previously-ready endpoint drop. After play-mode exit, the deferred compile
ends in a domain reload that stops the listener: the endpoint is down across the whole
compile, and when it returns the Editor is `ready` and the pending change has cleared.

The validation-host reproduction (`validation.md` in the archived
`surface-play-mode-compile-block`) measured the deferred compile as an ~15.5 s unreachable
window with play exit observed at ~57.6 s. `wait-for-compile` invoked in that state returned
`no_compile_observed`.

## Hypotheses to investigate

1. The pending signal clears as part of the reload, before the CLI could take a baseline.
2. A server-side compile epoch (incremented on `compilationFinished`) is enough for a caller
   that took a baseline before the reload, but not for one that starts after.
3. The persisted settle timestamp (`UnityPuerExec.SettledImportUtcTicks` in `SessionState`)
   survives the reload and can serve as a comparable "compiled after T" signal.
4. The honest answer is that a post-reload caller cannot distinguish the two cases, and the
   fix is to make the CLI drive the transition (so it always has a baseline) rather than to
   make a late call succeed.

## Decisions

(none yet — this is a spike; record the confirmed root cause here when known)

## Open Questions

- See the proposal's open questions. The reproduction should answer (1) and (3) directly by
  reading `/health` and `SessionState` across a staged play-exit compile.
