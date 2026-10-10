# Proposal

## Why

`openspec validate --all --strict` currently reports exactly two warning classes and
nothing else:

- **65 over-length requirement descriptions** across 20 capabilities. The validator
  flags any requirement whose description (the text between `### Requirement:` and its
  first `#### Scenario:`) exceeds 500 characters. Several are far past that
  (`formal-cli-contract` alone carries 22, one at 1836 characters).
- **11 capabilities whose `## Purpose` is still the placeholder** that `openspec archive`
  writes for a newly created spec: `cache-staleness-detection`,
  `cli-binary-packaging`, `cli-version-compatibility`, `compile-wait`,
  `editor-log-isolation`, `editor-session-discovery`, `openupm-release-helper`,
  `openupm-release-pipeline`, `readme-agent-onboarding`, `unit-test-github-action`,
  and `validation-temp-asset-cleanup`.

Both classes were surfaced by the archive step of `add-compile-generation-signal`
(whose four new requirements are themselves clean). They are durable-spec quality
problems, not product behavior problems: an over-long requirement packs several
behaviors into one block, so a reader cannot tell which behavior a scenario proves and a
future change cannot modify one behavior without carrying the rest. Left alone they
permanently fail `--strict` and mask any genuinely new strict warning.

No product, CLI, or Editor behavior changes. This is a restructure of durable spec text.

## What Changes

- **Split every over-length requirement into one-behavior requirements.** The description
  is reduced to one behavior under 500 characters; examples and edge cases move into
  scenarios. Existing scenarios are preserved: they move with the behavior they prove and
  are not rewritten, dropped, or merged. Normative meaning (SHALL/MUST statements,
  scenario WHEN/THEN outcomes) is unchanged.
- **Write a real `## Purpose` for the 11 placeholder capabilities** — one or two
  sentences naming what the capability is for, replacing the placeholder sentence.
- **Edit the main specs directly, with no delta specs.** A delta cannot express
  "same behavior, better structure", and inventing requirements to satisfy the delta
  machinery would fabricate spec-level change that does not exist. The change therefore
  sets `skip_specs: true`, and its acceptance gate is the strict validator plus the
  existing structural test, not a spec merge.
- **Sequence behind the in-flight changes whose deltas touch the same requirements.**
  Three active changes carry `MODIFIED`/`REMOVED` deltas over requirements this change
  would rewrite; their archive merge would overwrite the split. This change declares
  `blocked_by` on them and re-runs the strict validator after they land so anything newly
  surfaced by their merge is folded in.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

(none — no spec-level behavior changes; `skip_specs: true` is declared in
`.openspec.yaml`)

## Impact

- `openspec/specs/*/spec.md`: requirement text restructured in 20 capabilities
  (`agent-cli-discoverability-validation`, `api-updater-recovery`,
  `cache-staleness-detection`, `cli-version-compatibility`, `compile-error-surface`,
  `compile-wait`, `editor-log-isolation`, `editor-session-discovery`,
  `exe-origin-project-inference`, `exec-import-support`, `exec-warning-status`,
  `formal-cli-contract`, `import-change-refresh`, `log-brief`, `modal-dialog-surface`,
  `project-control-endpoint`, `repository-governance`, `response-file-output`,
  `runtime-guidance`, `validation-host-integration`); `## Purpose` written in the 11
  capabilities listed above. Five capabilities need both.
- No source, CLI, package, test-helper, or validation-host change.
- Existing structural guard `tests/test_openspec_spec_hygiene.py` (it mirrors the
  every-requirement-needs-a-scenario-and-SHALL rule) must keep passing. It is a guard, not
  the acceptance gate; the gate is `openspec validate --all --strict`.
- Sequencing: `blocked_by` = `add-play-mode-commands`,
  `root-relative-dot-directory-exclusion`, `scan-only-import-change-signal`. Each carries a
  `MODIFIED`/`REMOVED` delta over a requirement in `formal-cli-contract`,
  `import-change-refresh`, or `project-control-endpoint` that this change rewrites.
  `scan-only-import-change-signal` additionally holds a long `ADDED` requirement in its own
  delta (`project-control-endpoint`: "Health response exposes the pending refresh state")
  which must be split after it merges.
