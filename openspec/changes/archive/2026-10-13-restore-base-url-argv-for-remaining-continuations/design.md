## Context

`restore-base-url-exec-continuation-guidance` introduced selector-keyed `argv_templates` on the
`("exec", "running")` `wait-for-exec` candidate and a `_select_argv` helper that picks the first
variant whose selector is present in the guidance context. Every other candidate still has a
single `argv_template` naming `--project-path`, so base-url mode renders no `argv` for them even
when `base_url`, `request_id`, and `log_range_span` are all present.

## Goals / Non-Goals

**Goals:**

- Base-url continuations that name a command the CLI can run over `--base-url` carry a runnable
  `argv`.
- One selection mechanism, not a second ad-hoc branch.

**Non-Goals:**

- Changing which candidates are offered, or the record-presence rule.
- Changing project-path `argv`.
- Adding base-url variants to commands that do not accept `--base-url` (`get-log-briefs`,
  `get-blocker-state`, `resolve-blocker`) or to candidates whose originating response is
  project-path-only.

## Decisions

### Decision 1: Construct the variants from the authored project-path template

The project-path form stays the authored `argv_template`. After every matrix entry (including
dynamically-added entries and alias derivations) exists, a single normalization pass replaces
that template with the selector-keyed `argv_templates` pair: the authored `--project-path` form
and the same invocation addressed through `--base-url`. `_select_argv` remains the only selection
mechanism, so the two addressing modes cannot diverge.

Rationale: the alternative — hand-editing every candidate — is the same transformation repeated
40+ times, and is exactly where the two variants would drift. A derived construction keeps them
identical by construction, and the project-path rendering is provably unchanged.

### Decision 2: Only for candidates reachable under both selectors

Eligibility is checked on both ends of the continuation: the command the response comes from and
the command the candidate recommends must each accept `--base-url`. `get-log-briefs`,
`get-blocker-state`, and `resolve-blocker` accept only `--project-path`, so their candidates keep
the authored form, and a `resolve-blocker` response never produces base-url context, so it gains
no base-url variant even when its continuation names a base-url-capable command. A fabricated
selector flag would violate the live-surface rule.

### Decision 3: The project-path-only error sweep keeps its candidate without argv

`get-log-briefs` reads a local `Editor.log`; it has no base-url form. A base-url `exec` /
`wait-for-exec` / `wait-for-log-pattern` completed response therefore keeps the `get-log-briefs`
candidate and omits its `argv`, exactly as the existing "Incomplete log_range drops argv but
keeps the candidate" rule already prescribes for unfillable context. The durable success-path
requirement is reconciled so "complete invocation" is scoped to a selector the named command
accepts; the alternative (adding `--base-url` support to `get-log-briefs`) is a separate feature
and out of scope.

## Risks / Trade-offs

**[The normalization converts a candidate whose target does not accept `--base-url`]** → The
pass keys off an explicit project-path-only command set, and a unit test asserts that set equals
the commands whose parser lacks `--base-url`, so a new project-path-only command fails the test
rather than silently producing a fabricated flag.

**[A derived variant drifts from the authored one]** → Variants are derived, so they differ only
by the selector flag and placeholder. The regression suite renders every converted candidate
under both selectors, asserts the two differ only by the selector tokens, and parses the rendered
`argv` against the real command option surface.
