# Design

## Context

See `proposal.md` - Why for the two warning classes and their counts. The constraints
that shape the approach:

- The strict validator measures only the requirement **description** (from
  `### Requirement:` to the first `#### Scenario:`). Every warning is therefore fixable
  by moving text out of the description, without touching a single scenario.
- `formal-cli-contract` carries 22 of the 65 long requirements, so the work is
  mechanical and repetitive rather than deep; one capability dominates the count.
- Five capabilities need both a requirement split and a Purpose
  (`cache-staleness-detection`, `cli-version-compatibility`, `compile-wait`,
  `editor-log-isolation`, `editor-session-discovery`), so the two work streams meet in
  the same files and must be edited together.
- Three active changes hold `MODIFIED`/`REMOVED` deltas over requirements this change
  would rewrite, and their archive merge is authoritative over the main specs.
- The repository already treats `openspec/specs/` as the durable truth and
  `openspec/config.yaml` as repository-wide context. Nothing here moves text between
  them: the split requirements are still durable, testable statements and stay in
  `openspec/specs/`; no repo-wide convention is being promoted into a requirement or
  demoted into context.

## Goals / Non-Goals

**Goals:**

- `openspec validate --all --strict` reports 0 warnings: no requirement description over
  500 characters, no placeholder Purpose.
- Each affected requirement states exactly one behavior, with its scenarios preserved
  verbatim and its normative meaning unchanged.
- The change is auditable as a pure restructure: no added, removed, or changed
  externally observable behavior.

**Non-Goals:**

- No requirement is added, removed, renamed wholesale, or semantically edited.
- No spec file is created, deleted, or moved; capability paths are unchanged.
- No source, CLI, Editor package, test, tooling, or `config.yaml` change.
- The 22-requirement `formal-cli-contract` block is not treated as one exceptional task
  or rewritten by hand into a new document; it uses the same split rule as the rest.

## Decisions

### D1. Edit the main specs directly; declare `skip_specs: true`

A delta spec cannot express "same behavior, better structure". Using `MODIFIED` would
require copying 65 requirement blocks full replacement text and would officially record
65 behavioral changes, producing misleading change history and a large merge surface for
the three in-flight changes. `RENAMED` only covers name changes. The change therefore
declares `skip_specs: true` and edits `openspec/specs/*/spec.md` in place; the strict
validator on those files is the acceptance gate, which is a stronger structural check
than a delta merge.

**Alternatives considered:** one delta per capability with `MODIFIED` (rejected above);
leaving the text and suppressing the warning (rejected: `--strict` is the governance
signal and must stay meaningful).

### D2. Split rule: one behavior per requirement, ≤500 characters, scenarios move verbatim

For each flagged requirement: keep the leading behavior under the existing name and
description (trimmed to one behavior, ≤500 chars); extract each further behavior into a
new `### Requirement:` with its own description and the scenarios that prove it. A
scenario that proves two behaviors is copied to both requirements rather than reworded.
`SHALL`/`MUST` wording and WHEN/THEN outcomes are preserved. New names describe the
extracted behavior in the existing house style.

**Why keep the original name for the leading behavior:** active deltas match `MODIFIED`
requirements by header, cross-references name requirements, and renaming everything adds
churn without fixing a warning. **Alternative:** rename every split part for uniformity
(rejected: churn and merge friction).

**Why not shorten by deleting detail:** the validator's own guidance is to move examples
and edge cases into scenarios, not to drop them. Deleting normative detail would be a
semantic change and is out of scope.

### D3. Purpose authoring is derived, not invented

Each placeholder is replaced with one or two sentences naming what the capability is
for, read off its existing requirements and any `how-to-run.md` beside it. A Purpose is a
description of intent, so it adds no requirement and must not assert behavior the
requirements do not already state.

### D4. Sequence with `blocked_by`, then re-baseline

`blocked_by` names `add-play-mode-commands`, `root-relative-dot-directory-exclusion`,
and `scan-only-import-change-signal`. The first two carry `MODIFIED` deltas over
`formal-cli-contract` and `import-change-refresh` requirements that this change rewrites;
the third `REMOVED`/`MODIFIED` the `project-control-endpoint` pending-refresh
requirement and adds a long replacement requirement in its own delta. Archiving them
first means this change rewrites the merged result once, instead of being overwritten.
After they archive, this change re-runs `openspec validate --all --strict` and folds any
newly surfaced warning into its tasks before starting.

**Alternative:** fix the non-overlapping capabilities now and the 5 overlapping ones
immediately (rejected: produces a split that the deltas silently revert, and a second
cleanup pass).

### D5. Verification is validator plus an explicit semantic check

`openspec validate --all --strict` proves the structural goal; it cannot prove nothing
was reworded into a different requirement. Each capability's diff is therefore reviewed
for: unchanged scenario text, unchanged SHALL/MUST statements, and no new normative
claim. `tests/test_openspec_spec_hygiene.py` and the default unit suite confirm nothing
downstream depended on the old shape.

## Risks / Trade-offs

- **Semantic drift while splitting** → keep descriptions to extraction only, move
  scenario text verbatim, and diff-check the SHALL/MUST count per capability. A behavior
  that is genuinely inseparable stays under 500 characters by moving its examples into
  scenarios.
- **A reference breaks when a requirement is renamed** → grep the repository (specs,
  proposals, code comments, tests) for the name before renaming; keep the leading
  behavior under the original name.
- **An in-flight delta reverts the split at archive time** → `blocked_by` plus the
  post-dependency re-baseline in D4; do not start apply while a dependency is unarchived.
- **Placeholder Purpose contradicts its requirements** → derive the sentence from the
  capability's own requirements and scenarios, not from memory or inference.
- **A later change re-inflates a description** → not prevented here; the strict
  validator is the ongoing guard, which is why this change restores its signal rather
  than silencing it.

## Migration Plan

Pure text edit of `openspec/specs/*/spec.md`; rollback is `git revert` of the spec
commits. Apply does not start while a `blocked_by` change is unarchived. Within the
single post-dependency pass: re-run the strict validator to capture the merged work list
(the dependencies will have added and removed requirements), write the placeholder
Purposes first because they are independent and cheap, then split requirements
capability by capability starting with `formal-cli-contract`.
