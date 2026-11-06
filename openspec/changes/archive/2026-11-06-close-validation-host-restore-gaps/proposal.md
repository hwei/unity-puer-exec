# Proposal

## Why

These are follow-ups from the four-follow-up closeout (archived in commit
`c3f5bb9`).

1. **Prepare cannot be undone.** `tools/prepare_validation_host.py` rewrites the
   host's `Packages/manifest.json`, and Unity then regenerates
   `packages-lock.json`. The tool has no inverse for that rewrite. The embedded
   shadow already has a paired clear/restore. So after every real-host session,
   a maintainer has to run a hand-written `git checkout` on the host to return
   it to the state it was in before. In the last session that `git checkout`
   was also blocked by the agent's permission check.
2. **The release helper names a fix but not the command.** When
   `release_openupm` finds an embedded copy that is behind or out of date, it
   says "remove the embedded copy so the file: dependency wins". The tool that
   does this safely, `prepare_validation_host.py --clear-embedded-shadow`,
   already exists. The message does not name it, so an operator may move the
   directory by hand, which is the practice the run instructions warn against.

## What Changes

- `prepare_validation_host.py` saves the host's original `manifest.json` and
  `packages-lock.json` into a host-local backup the first time it rewrites the
  manifest.
- A new `--restore-manifest` operation puts both files back. It works like the
  shadow restore: it does not delete files or run version control, and it
  reports its result as JSON. It refuses while an Editor is serving the host,
  supports `--dry-run`, and runs again safely with no change.
- The restore refuses when `manifest.json` changed after prepare wrote it, so it
  never overwrites someone else's edit.
- The remediation text for `release_openupm` errors caused by an embedded copy
  (`host_package_version_mismatch`, `host_package_stale`) names the exact
  `--clear-embedded-shadow` command and its `--restore-embedded-shadow`
  counterpart.
- The run instructions add a teardown step for the manifest restore.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `validation-host-integration`: add requirements for the reversible manifest
  rewrite (backup on first rewrite, guarded restore, preview, host-freedom
  refusal).
- `openupm-release-helper`: the remedy that an embedded-copy refusal offers names
  the repository-owned clear command.

## Impact

- `tools/prepare_validation_host.py`: backup on write, the new
  `--restore-manifest` flag, which cannot be combined with the shadow flags, and
  reuse of `host_freedom_refusal`.
- `tools/release_openupm.py`: two error-message strings.
- Tests: `tests/test_prepare_validation_host_tool.py` and
  `tests/test_release_openupm_tool.py`, both mocked. This change does not need a
  real host.
- Docs: `openspec/specs/validation-host-integration/how-to-run.md`, teardown
  section.
- Host side effect: one new host-local backup directory, next to the existing
  embedded-shadow backup.
