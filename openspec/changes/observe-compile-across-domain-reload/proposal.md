## Why

When the Editor leaves play mode with a deferred compile (`recompile_after_finished_playing`
or `stop_playing_and_recompile`), Unity compiles the pending change and then reloads the
domain. `AssemblyReloadEvents.beforeAssemblyReload` stops the control listener, so `/health`
is unreachable for the duration of the reload. If `wait-for-compile` is invoked once the
endpoint is back, the Editor is already `ready`, the change signal has cleared, and no
`compiling` state was ever observable. The command returns `no_compile_observed`.

Observed while landing `surface-play-mode-compile-block` on the validation host: the
deferred compile ran on play exit, but `wait-for-compile` returned `no_compile_observed`
because the compile edge was hidden behind the reload.

This is a false negative against the command's purpose: a compile did happen, and the
caller is told none was observed. An agent that branches on `no_compile_observed` may
re-trigger a compile or read stale compile messages.

## What Changes

This spike determined whether the hidden compile can be made observable and by what signal.
The investigation (reproduction, timeline, and signal comparison in `design.md`) concluded:

- The deferred compile is Unity's **forced synchronous recompile**. `beforeAssemblyReload`
  stops the listener before compilation finishes, so `/health` never serves `compiling`;
  the endpoint is unreachable for the whole compile + reload and returns already `ready`.
- `CompilationPipeline.compilationFinished` **does** fire for it, **before** the reload, and a
  `SessionState`-backed compile generation survives the reload.
- `session_marker` and `SettledImportUtcTicks` are **reload** epochs, not compile epochs:
  they also advance on a reload that compiled nothing.
- The only reliable discriminator is a compile-specific generation combined with a baseline
  taken before the transition; a caller that starts after the reload without a baseline
  cannot be satisfied.

**Recommendation:** expose a monotonic compile generation on `/health` and let a caller that
holds a pre-transition baseline settle the compile from it. The implementation is split into
the follow-up change `add-compile-generation-signal`.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

(none — no durable requirement changes here; the requirements for the recommended signal are
written in the follow-up change `add-compile-generation-signal`)

## Impact

(none in this spike; the implementation impact — server, protocol, CLI, and tests — is
recorded in `add-compile-generation-signal`)

## Open Questions

(resolved by the investigation; see `design.md`)
