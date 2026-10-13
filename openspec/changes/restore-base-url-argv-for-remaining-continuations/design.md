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
- Adding base-url variants to commands that do not accept `--base-url`.

## Decisions

### Decision 1: Reuse `_select_argv`, do not add selection logic

`_select_argv` already treats a candidate as a set of selector-keyed variants and returns the
matching `argv_template`. Converting the remaining candidates is a data change in
`GUIDANCE_MATRIX`: replace `argv_template` with `argv_templates` and add the `--base-url`
variant. No new code path, so the two mechanisms cannot diverge.

### Decision 2: Only for commands that accept both selectors

A variant is added only where the target command's parser accepts `--base-url`. Candidates whose
command ignores the selector, or that build their invocation from payload fields rather than a
selector, stay as they are — a fabricated selector flag would violate the live-surface rule.

## Risks / Trade-offs

**[A variant is added for a command that does not accept `--base-url`]** → The unit suite already
asserts candidate `argv` uses only live surface; the added coverage asserts the rendered `argv`
for each converted selector.
