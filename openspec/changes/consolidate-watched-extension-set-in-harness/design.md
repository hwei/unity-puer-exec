## Context

`_watched_compile_triggering_extensions()` reads the watched set from the durable `exec --help-args`
statement and is already used by `_write_compile_triggering_probe`. `_drop_latched_temp_scripts`
and `_drop_unimported_compile_probes` still hardcode `(".cs", ".asmdef", ".asmref", ".rsp")`.

## Goals / Non-Goals

**Goals:**

- One source for the watched set inside the harness.

**Non-Goals:**

- Changing what is deleted or when. The failure mode these helpers address (a leftover probe) is
  unchanged.
- Touching product code or the Editor-side tracker.

## Decisions

### Decision 1: Reuse the existing derivation, accept the coupling

The cleanup helpers call the same `_watched_compile_triggering_extensions()` used at staging. A
reworded help statement now raises in cleanup too, which is the intended loud failure rather than
silent drift. Cleanup already runs only inside the opt-in real-host suite.

## Risks / Trade-offs

**[Cleanup now depends on the help statement]** → Accepted, and consistent with the staging
helper. The failure is a clear assertion, not a wrong deletion.
