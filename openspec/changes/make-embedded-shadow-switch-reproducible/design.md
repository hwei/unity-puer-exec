# Design

## Context

See `proposal.md` — Why. What already exists:

- `tools/prepare_validation_host.py` rewrites the host `Packages/manifest.json` `dependencies` entry
  to the repository-local package, declares the package in `testables`, and reports
  `embedded_package_shadowing`, `embedded_package_path`, and `embedded_package_paths`. Detection is
  by the `name` declared in a candidate `package.json` among the immediate children of `Packages/`,
  which is how Unity identifies an embedded package — a renamed directory still shadows.
- `--dry-run` prints the intended dependency and `testables` list without writing.
- The real-host suite decides whether the host project is free from project-local state alone: the
  project's Unity lockfile, and the Editor-published endpoint at `Temp/UnityPuerExec/endpoint.json`.
- Hosts in the wild carry the embedded copy as **tracked files in the host's own repository**, with a
  published `CLI~/unity-puer-exec.exe` inside it. One observed host also carries an empty
  `.unity-puer-exec-embedded-backup/<name>-<date>/` skeleton at its root — the residue of a previous
  hand-rolled clear that was restored file-by-file.

## Goals / Non-Goals

**Goals:**

- One command each way, so the sequence is reproducible by an agent rather than reconstructed from
  the run instructions each time.
- An exact inverse: restore puts back precisely what clear moved, and a clear/restore round trip
  leaves the host's git status as it was found.
- Refusal over damage: a busy host, an occupied restore target, or an unparseable state reports a
  named reason instead of acting.

**Non-Goals:**

- No git operations on the host. No commit, no stash, no index write, no `checkout`. The host's own
  version control is the operator's, and the tool has no business deciding what it records.
- No deletion, ever, in either direction.
- No syncing of package content between the repository and an embedded copy. That is the release
  helper's `--sync-host-version` concern, which already refuses on divergence; this change moves
  directories, it does not reconcile them.
- No change to shadowing *detection* or to the existing report fields. They stay as landed.

## Decisions

### D1. Filesystem move, not a git operation

The embedded copy is tracked in the host repository, so a move shows up there as deletions. That is
the correct visible state: it says out loud that the host is temporarily wired differently, and it is
what an operator restoring by hand produces anyway. The alternatives were rejected because they make
decisions that belong to the operator — `git stash` and `git rm --cached` write the host's index, and
a `git checkout`-based restore would discard local edits to the embedded copy that the tool has no
way to judge.

### D2. The backup location adopts the convention already in the wild

Clear moves each shadowing directory to `<host root>/.unity-puer-exec-embedded-backup/<directory name>-<YYYYMMDD>/`,
outside `Packages/` as the spec requires. Adopting the observed path means an existing skeleton is
recognizable rather than competing with a second convention, and a same-day repeat does not collide
because the moved directory is gone. A collision on the backup path — a previous clear never
restored — refuses and names the occupied backup rather than nesting or overwriting.

### D3. Restore is driven by the backup, not by a re-scan

Restore moves back what the backup directory actually holds, and refuses when the corresponding
`Packages/` child already exists. It does not try to merge, and it does not consult git to decide
what "should" be there. A restore target that is occupied means someone reinstalled the package by
hand, and guessing which copy wins is exactly the ambiguity the release helper refuses on for the
same reason.

### D4. Both directions require a free host

Moving a package out of `Packages/` under a live Editor leaves its AssetDatabase and Library
describing a package that is no longer there, and moving one back can be picked up mid-import. Both
directions therefore check the same project-local boundary the real-host suite uses — the project's
Unity lockfile and the Editor-published endpoint — and refuse with a named reason when the host is
not free. This is a check, not a kill: the tool never stops an Editor.

### D5. Report shape extends the existing envelope

`status` becomes one of `cleared`, `restored`, `unchanged`, `refused`, `dry-run`, or `updated`, and
the payload adds `backup_path` and `reason` alongside the existing `embedded_package_shadowing`,
`embedded_package_path`, and `embedded_package_paths`. Reporting the post-operation shadowing value
is what lets a caller verify the clear worked without a second invocation, and keeping the existing
fields untouched is what keeps every current consumer — the real-host suite's skip checks and the
release helper's host checks — working unchanged.

### D6. `--dry-run` covers the new operations too

The existing flag already prints intent without writing. Extending it to clear and restore keeps one
way to ask "what would this do to my host", which matters more for an operation that moves tracked
files than for one that edits a manifest.

## Risks / Trade-offs

- **[An operator clears and never restores, leaving the host wired to the repository package]** →
  The clear report names the backup path and states that the host now loads repository code rather
  than its own embedded copy; restore refuses on an occupied target rather than guessing; and the
  run instructions pair the two commands in one section so the inverse is discoverable from the
  forward direction.
- **[A host has several shadowing directories]** → Detection already names all of them, so clear
  moves all of them into one dated backup and restore puts all of them back. A partial clear is not a
  state the tool can produce.
- **[The lockfile check disagrees with reality on a stale lock]** → The check reports the evidence it
  used, and refusal is the safe direction: an operator who knows the lock is stale can remove it,
  which is the same recovery the suite already relies on.
- **[A future consumer depends on the old `status` vocabulary]** → The existing values (`updated`,
  `unchanged`, `dry-run`) keep their meanings; the new values only appear for the new operations, so
  no current caller sees a value it did not ask for.

## Migration Plan

Tooling-only. No state to migrate: a host that was cleared by hand restores by hand exactly as
before, and the empty backup skeletons already present are inert. Rollback is dropping the flags,
which restores today's behaviour because nothing else in the repository calls them yet; the run
instructions revert to describing the manual move.
