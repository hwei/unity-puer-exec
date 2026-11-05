# Proposal

## Why

Validation-host preparation already detects an embedded `com.txcombo.unity-puer-exec` shadowing the
repository-local package and reports it machine-readably, and the run instructions already state that
clearing it requires moving the directory out of `Packages/`. Nothing performs that move. Every
real-host validation run against a host wired the way a consumer installs the package therefore
starts with a hand-rolled sequence — move the tracked embedded directory aside, run
`prepare_validation_host.py`, confirm `embedded_package_shadowing: false`, and remember to put it
back afterwards — and ends with the host's git tree dirty if the operator forgets a step.

`fix-unchanged-content-refresh-loop` paid that cost directly: the validation host carried an
embedded 0.12.0 copy, so the shadow had to be cleared by hand before any of its evidence counted,
and restored by hand afterwards. The host was left with an empty backup skeleton from an earlier
session doing the same dance, which is the visible residue of a step that should be a command.

## What Changes

- `tools/prepare_validation_host.py` gains a paired operation: clear an embedded shadow by moving
  the shadowing directory out of `Packages/` into a host-local backup, and restore it by the exact
  inverse move.
- Clearing never deletes. A restore refuses rather than merging when the target path is already
  occupied, so a hand-edited embedded copy is surfaced instead of silently overwritten.
- Both directions refuse when the host project is not free — an Editor serving it would have a
  package removed from under its AssetDatabase — using the same project-local boundary the real-host
  suite already decides freedom from.
- Both report machine-readably in the same envelope preparation already uses, naming the backup path,
  every shadowing directory acted on, and the resulting `embedded_package_shadowing` value, so a
  caller can tell `cleared` from `unchanged` from `refused`.
- Both are idempotent: clearing an already-clear host and restoring an already-restored host report
  `unchanged` rather than failing.
- The real-host run instructions name the command instead of describing a manual move.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `validation-host-integration`: adds a requirement that preparation can clear and restore an
  embedded shadow as a repository-owned, refusing-when-unsafe, never-deleting operation; and amends
  "Real-host run instructions state how embedded shadowing is cleared" so the instructions name that
  operation rather than only stating that a move is required.

## Impact

- **Tooling**: `tools/prepare_validation_host.py` (new paired flags plus the freedom check and the
  report fields).
- **Tests**: `tests/test_prepare_validation_host_tool.py` gains coverage for clear, restore,
  idempotence, refusal on an occupied target, refusal on a busy host, and the report shape.
- **Docs**: `openspec/specs/validation-host-integration/how-to-run.md` — the shadowing section names
  the command; the release-time section is unaffected because it already reasons about the loaded
  copy rather than about how it got there.
- **Product**: none. No package or CLI surface changes.
- **Hosts**: the operation writes only inside the target host project (a backup directory at the host
  root and the `Packages/` child it moves). It does not touch the host's git index and creates no
  commit; the host's `git status` shows the move, which is the honest and reversible state.
- **Upstream**: inherits the shadowing detection and reporting landed for
  "Validation host preparation reports embedded package shadowing" and "Shadowing report is
  machine-readable and names all matches"; those requirements are unchanged.
