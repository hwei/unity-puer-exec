# Tasks

## 1. Dependency gate and merged work list

- [ ] 1.1 Confirm both `blocked_by` changes are archived (`root-relative-dot-directory-exclusion`, `scan-only-import-change-signal`) and that this change is no longer reported as blocked. Verify: each name appears under `openspec/changes/archive/` via `git log --oneline -- openspec/changes/archive`, and `python tools/openspec_backlog.py list --backlog` no longer lists this change as ineligible for that reason.
- [ ] 1.2 Re-run `openspec validate --all --strict --json` on the merged specs and record the authoritative work list — every capability with a long-requirement warning (requirement header and character count) and every placeholder `## Purpose` — to `.tmp/spec-strict-worklist.json`. Verify: the file exists, its long-requirement count and placeholder count equal the validator's issue counts, and it names any requirement the dependencies' merge newly introduced (for example the `project-control-endpoint` pending-refresh replacement from `scan-only-import-change-signal`).

## 2. Placeholder purposes

- [ ] 2.1 Write a real `## Purpose` for `cache-staleness-detection`, `cli-binary-packaging`, `cli-version-compatibility`, `compile-wait`, and `editor-log-isolation`, each derived from its own requirements (and its adjacent `how-to-run.md` where present), one or two sentences, no behavior the requirements do not state. Verify: `openspec validate <capability> --strict` reports no placeholder warning for each of the five.
- [ ] 2.2 Write a real `## Purpose` for `editor-session-discovery`, `openupm-release-helper`, `openupm-release-pipeline`, `readme-agent-onboarding`, `unit-test-github-action`, and `validation-temp-asset-cleanup` under the same rule. Verify: `openspec validate <capability> --strict` reports no placeholder warning for each of the six, and `openspec validate --all --strict` reports zero placeholder warnings.

## 3. Requirement splits

- [ ] 3.1 Split every long requirement in `formal-cli-contract` (the 22-requirement majority): keep the leading behavior under the existing name and description, extract each further behavior into its own requirement below 500 characters, and move the proving scenarios with it verbatim. Verify: `openspec validate formal-cli-contract --strict` reports no long-requirement warning, the count of `#### Scenario:` lines is unchanged from `HEAD`, and every resulting requirement keeps a `SHALL`/`MUST` statement.
- [ ] 3.2 Split every long requirement in `runtime-guidance` (8) and `validation-host-integration` (8). Verify: `openspec validate runtime-guidance --strict` and `openspec validate validation-host-integration --strict` report no long-requirement warning, and each file's `#### Scenario:` count is unchanged from `HEAD`.
- [ ] 3.3 Split every long requirement that survives in `import-change-refresh` and `project-control-endpoint` after the dependency merges, including any long requirement the merged `scan-only-import-change-signal` replacement introduced. Verify: `openspec validate import-change-refresh --strict` and `openspec validate project-control-endpoint --strict` report no long-requirement warning, and each file's `#### Scenario:` count is unchanged from the pre-split text of that merged state.
- [ ] 3.4 Split every long requirement in the remaining capabilities named by the work list — among them `agent-cli-discoverability-validation`, `api-updater-recovery`, `cache-staleness-detection`, `cli-version-compatibility`, `compile-error-surface`, `compile-wait`, `editor-log-isolation`, `editor-session-discovery`, `exe-origin-project-inference`, `exec-import-support`, `exec-warning-status`, `log-brief`, `modal-dialog-surface`, `repository-governance`, and `response-file-output`. Verify: `openspec validate --all --strict` reports zero long-requirement warnings.

## 4. Integration verification

- [ ] 4.1 Run the full strict gate: `openspec validate --all --strict` and `openspec validate --all`. Verify: zero warnings and zero failures, with the output recorded; ignore nothing and suppress nothing.
- [ ] 4.2 Audit semantic preservation per touched capability: scenario text unchanged, `SHALL`/`MUST` statement count unchanged, and no normative claim added. Verify: a recorded per-capability summary (scenario count and SHALL/MUST count from `git show HEAD:<path>` versus the working tree) shows equality for every touched spec, and `git diff` contains no rewritten WHEN/THEN line.
- [ ] 4.3 Run `python -m unittest tests.test_openspec_spec_hygiene` and the default unit suite from `openspec/specs/validation-host-integration/how-to-run.md`. Verify: the structural guard passes and the suite reports OK.

## Workflow follow-up

- Recommend `git commit`, then `openspec archive remediate-spec-strict-warnings` (the change declares `skip_specs: true`, so archiving carries no spec merge), then a final `git commit`.
- After archive, re-run `openspec validate --all --strict` to confirm no later change re-inflated a requirement description, and treat that validator as the standing guard for this class of drift.
