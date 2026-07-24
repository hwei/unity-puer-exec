## Context

Upstream changes already closed the rest of the 2026-07-23 feedback slice:

- `enforce-cli-version-compatibility` — version identity and hard mismatch refusal.
- `improve-exec-and-observation-help` — help-only mental model (JsEnv isolation, PlayMode timing, `log_range.start` vs `.end`).
- `normalize-cli-usage-error-responses` — parse-level usage errors and usage-status matrix coverage.

What remains is the success-path gap those changes explicitly deferred: empty matrix entries for `("exec", "completed")` and `("wait-for-log-pattern", "completed")`, plus the same shape on `("wait-for-exec", "completed")`. The interview evidence still holds — a pattern match is not an error sweep, and agents hand-copy offsets when the CLI could emit a complete argv.

Current mechanics:

- `GUIDANCE_MATRIX` entries for those three statuses are empty (`{}`).
- `_build_guidance_context` reads only argparse `args` (and `request_id`); it never sees `log_range` already on the payload.
- `_build_argv` substitutes whole template items of the form `{key}`; it does not interpolate inside a larger string.
- `exec` / `wait-for-exec` inject `log_range` *before* `_inject_guidance_into_response`, so the envelope already has the values at attach time.
- `wait-for-log-pattern` success injects `log_range` but never calls `_attach_guidance`.
- Bridge `BuildExecResponseJson` already carries top-level `session_marker` on completed/failed/running/warning; this design does not re-open a protocol change for that field.

This content belongs in `openspec/specs/runtime-guidance/`, not `openspec/config.yaml`: it is a durable, testable product contract for machine-readable follow-up guidance.

## Goals / Non-Goals

**Goals:**

- Give agents a copyable error-sweep follow-up on the three success statuses that already expose an observation window via `log_range`.
- Keep candidate selection static and keyed by `(command, status)`.
- Allow argv *values* to be filled from CLI-owned envelope fields without reopening "steer guidance from script `result`."
- Make the `wait-for-log-pattern` success path attach guidance at all.
- State, briefly, that a pattern match is not an all-clear for errors/warnings.

**Non-Goals:**

- New commands, statuses, exit codes, or C# protocol fields.
- Prefilling `wait-for-log-pattern` as a success follow-up (needs a caller-supplied `--pattern`).
- Binding `--expected-session-marker` into the error-sweep argv (`get-log-briefs` has no such flag; observation-marker guards stay on wait commands).
- Teaching base-url selector argv variants across the whole matrix (existing project-path-only templates stay as-is).
- Replacing or inventing `--include-new-error-briefs` (withdrawn in the interview).
- Help-surface prose beyond what the matrix / `--help-status` already derives from entries.

## Decisions

### D1: Scope three success statuses, one shared candidate shape

Fill:

| key | `next_steps` | `situation` |
|---|---|---|
| `("exec", "completed")` | error-sweep | none |
| `("wait-for-exec", "completed")` | error-sweep | none |
| `("wait-for-log-pattern", "completed")` | error-sweep | short "match ≠ no new errors" |

`wait-for-exec` was not named in the original deferred "proposal B" label, but it carries the same `log_range` and the same empty matrix entry. Including it avoids a near-duplicate follow-up change.

**Alternative considered:** only `exec` + `wait-for-log-pattern`. Rejected — leaves an identical hole on the normal async completion path.

### D2: One fully constructible follow-up — the error sweep

Candidate:

```
get-log-briefs
  --project-path {project_path}
  --range {log_range_span}
  --levels error,warning
```

with `when` text that says this re-checks the observation window for new errors/warnings (and, for the log-pattern case, that a match alone does not prove the window was clean).

No second candidate that needs a free-form `--pattern`. Incomplete argv is worse than a single complete one.

**Alternative considered:** also suggest `wait-for-log-pattern` without argv. Rejected — noisy; help already covers that workflow.

### D3: Precompute `log_range_span` rather than extending the template engine

`_build_argv` only replaces items that are entirely `{key}`. Building a range token as one context value:

```
log_range_span = "{start}-{end}"
```

avoids inventing in-string interpolation. Both ends MUST be present; if either is missing, omit the context key so `_build_argv` drops `argv` while still emitting `command` + `when`.

**Alternative considered:** change `_build_argv` to support `{start}-{end}` inside a single item. Rejected for this change — wider blast radius for no product gain.

### D4: Enrich guidance context from the payload being annotated, after `log_range` injection

Extend `_attach_guidance` (or a helper it calls) to copy CLI-owned fields from `payload` into the template context:

- `log_range.start` / `log_range.end` → `log_range_span` when both are present
- existing args-derived keys unchanged (`project_path`, forwarded `--unity-log-path`, etc.)

Do **not** read `result`, script-authored fields, or free-form `error` text to choose or order candidates. Reading `error` for situation *hints* remains the separate, already-specified path (`_maybe_hint_puer_prefix`).

Ordering invariant (already true for exec / wait-for-exec; must be established for wait-for-log-pattern):

```
inject log_range  →  attach guidance  →  emit
```

**Alternative considered:** thread `log_range` through `_build_guidance_context(args, …)` only. Rejected — those values are not on `args`; the payload is the source of truth and is already in hand at attach time.

### D5: Wire the missing success attach on `wait-for-log-pattern`

Call `_attach_guidance(payload, "wait-for-log-pattern", "completed", args)` after log-range injection on the success return. Failure paths already attach; only success is missing.

### D6: Spec shape — ADDED success-path requirement + MODIFIED matrix clarification

- **ADDED**: success statuses listed above SHALL carry the error-sweep candidate (and the log-pattern situation).
- **MODIFIED**: the existing "static matrix / does not depend on response payload content" requirement is refined so candidate selection stays command+status-only and script-`result`-free, while argv construction is explicitly allowed to read CLI-owned envelope fields such as `log_range`.

Using MODIFIED (full requirement copy) avoids archive-time loss and prevents the old scenario title from being read as a ban on all payload reads.

### D7: No formal-cli-contract delta in this change

`log_range` on exec responses is already required. Bridge `session_marker` on exec bodies already exists and is not needed for the error-sweep argv. Adding a formal-cli-contract requirement for `session_marker` on every exec status would be a separate, broader contract change.

## Risks / Trade-offs

- **`argv` absent when `log_range` or selector context is incomplete** → Mitigation: still emit `command` + `when`; agent can build the invocation from the envelope. Same pattern as other matrix entries that drop argv when a placeholder is missing.
- **Agents treat the error-sweep as mandatory after every success** → Mitigation: `when` text frames it as the check to run when the caller needs confidence about new errors/warnings, not as a required next hop.
- **Future implementer re-reads the old "no payload dependence" rule as forbidding `log_range` argv fills** → Mitigation: MODIFIED requirement states the split in normative language with scenarios for both sides.
- **Success-path guidance increases response size slightly** → Mitigation: one candidate, compact argv; still subject to `--suppress-guidance` and `--response-file`.
- **`brief_sequence` already on the response may make the sweep redundant in some cases** → Mitigation: accepted. `brief_sequence` is a compact hint; `get-log-briefs` remains the structured detail path, and the matrix already points there from other statuses. The win is a ready-made argv with this run's offsets.

## Migration Plan

- Purely additive CLI behavior on existing success statuses; no migration for callers.
- Archive order: no peer active change currently shares these requirement names; archive after apply as usual.
- Rollback: revert the matrix entries and context enrichment; responses return to empty success guidance.

## Open Questions

None blocking propose. Apply-time detail only: exact `when` / `situation` wording can be tightened against test assertions without further design.
