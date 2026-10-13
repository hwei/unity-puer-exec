## Context

`get-log-briefs` currently accepts only `--project-path` and reads a local `Editor.log`
(`cli/python/unity_puer_exec_runtime.py`, `run_get_log_briefs`). Base-url mode therefore has no
runnable error sweep, and the previous change kept its candidate while omitting `argv`.

The CLI already knows how to resolve a log path for a base-url endpoint: `unity_session.get_log_source`
probes `/health` and uses the Editor-reported `Application.consoleLogPath`
(`console_log_path`), which is what `get-log-source --base-url` already does. But base-url
`exec`/`wait-for-exec` capture their advertised `log_range` offsets through `_resolve_log_path`,
which ignores the endpoint report and uses the platform default. That inconsistency must be fixed
for the error sweep to read the file its offsets refer to.

## Goals / Non-Goals

**Goals:**

- `get-log-briefs` works in base-url mode against a same-machine endpoint.
- One log-source resolution path for base-url observation, shared by offset capture and
  `get-log-briefs`.
- Base-url completed guidance regains a complete, runnable error-sweep invocation.

**Non-Goals:**

- Transferring log content over the network. A remote Editor is explicitly out of scope; the
  endpoint is assumed to share the caller's filesystem, exactly as the base-url `log_range`
  contract already assumes.
- Changing project-path behavior or the range/level/index/full-text filters.

## Decisions

### Decision 1: Reuse `get_log_source` for every base-url log operation

Base-url `get-log-briefs` and base-url `log_range` offset capture both resolve their path through
`unity_session.get_log_source(base_url=...)`. This honors the durable resolution order (an
explicit path, then the Editor-named console log path, then the platform default) and keeps the
offsets and the briefs on the same file. `_resolve_log_path` gains a base-url branch that consults
this; the existing project-path branch keeps using the session's effective log path.

### Decision 2: Reject `--unity-log-path` in base-url mode

`--unity-log-path` names a project-host file, so it is meaningful only in project-path mode.
Base-url mode rejects it via the existing `validate_project_mode_only` usage error, consistent
with the other selector-driven commands.

### Decision 3: No unverified default when nothing resolves

`get_log_source` already treats the platform default as a last resort and returns no source when
even that file is absent. `get-log-briefs --base-url` reports `no_observation_target` in that case
instead of parsing a path that does not exist. For offset capture, a missing source simply yields
a zero offset, as elsewhere.

### Decision 4: Guidance follows from the parser change

Making `--base-url` a live flag removes `get-log-briefs` from `_PROJECT_PATH_ONLY_COMMANDS`. The
existing selector-variant construction then gives the three completed `get-log-briefs` candidates
(and the `get-log-briefs` completed `get-log-source` candidate) base-url variants automatically;
the drift test that pins `_PROJECT_PATH_ONLY_COMMANDS` against the live parser fails until the set
is updated, so the two cannot silently diverge.

## Risks / Trade-offs

**[A base-url endpoint on a different machine yields a wrong or unreadable path]** → The path
comes from the Editor's own `/health` report, and the platform default is used only as a last
resort when it exists. The same-filesystem assumption is documented and is already the basis of
base-url `log_range`; remote support is a separate, explicitly deferred feature.

**[Resolving through `/health` adds probes to base-url observation commands]** → The probe is a
localhost HTTP call the command already makes against the same endpoint; the reported path is the
only way to honor a custom `-logFile`, and without it the advertised offsets could refer to a
different file.
