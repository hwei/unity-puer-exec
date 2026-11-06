# Design

## Context

What still holds from the embedded-shadow clear/restore work:

- `prepare_validation_host.py` already has two operations that cannot be
  combined: `--clear-embedded-shadow` and `--restore-embedded-shadow`.
- They share the following:
  - a host-local backup root, `<host>/.unity-puer-exec-embedded-backup/`;
  - `host_freedom_refusal`, which checks the lockfile and the published
    endpoint;
  - `--dry-run` previews;
  - the JSON envelope (`status`, `backup_path`, `reason`, `moved`) and
    `EXIT_REFUSED = 2`.

The gap: the default mode, a manifest rewrite through `write_manifest`, has no
inverse. Once the host Editor resolves packages, Unity rewrites
`packages-lock.json`. The tool never touches that file directly, but the host's
git status still ends up with two dirty files.

## Goals / Non-Goals

**Goals:**
- A teardown command that returns the host's manifest and lock file to their
  pre-preparation state, under the same safety rules as shadow switching.
- Release-helper refusals that point at that tool's commands.

**Non-Goals:**
- Restoring other host files the Editor writes during a run. The
  `ProjectSettings.asset` write is fixed at its source by
  `stop-play-persisting-run-in-background`.
- A single "teardown everything" command. The two restores stay separate,
  because each one owns distinct state and can refuse independently.

## Decisions

### D1: Backup on first write, in a separate backup root

`<host>/.unity-puer-exec-manifest-backup/` holds:

- `manifest.json`: the original;
- `packages-lock.json`: the original, when one existed;
- `written-manifest.sha256`: a hash of the content prepare last wrote.

The backup is taken only when the tool is about to write the manifest and no
backup exists yet. A later run, for example one that only adds `testables`,
updates `written-manifest.sha256` but keeps the originals. The originals must
always describe the pre-preparation host.

Alternative: reuse `.unity-puer-exec-embedded-backup/`. Rejected because the
shadow clear treats that root's children as moved package directories, and its
"empty skeleton" and "occupied" logic would have to learn to skip foreign files.
A sibling root keeps both operations simple.

Alternative: run `git checkout` on the host. Rejected because it contradicts the
existing rule of no version-control operations on the host, and hosts are not
guaranteed to be git working trees.

### D2: Foreign-edit guard uses the written-content hash

Before restoring, the tool hashes the current `manifest.json` and compares it
with `written-manifest.sha256`. If they differ, it refuses with
`manifest_modified_since_prepare`. The lock file is not guarded: Unity always
regenerates it, so a guard there would block every real restore.

### D3: Restore moves the files back, then removes only tool-owned metadata

The originals are moved with `os.replace` over the current files. After a
successful restore, the sidecar hash and the then-empty backup root are
removed. This matches how the shadow restore cleans up its own empty root:
nothing the host owned is deleted.

If the host had no `packages-lock.json` before preparation, the restore leaves
the regenerated one in place and reports it in a `left_in_place` field. Removing
it would mean deleting a file, which the existing rule forbids.

### D4: Flag shape

`--restore-manifest` joins the existing group of mutually exclusive flags. It
reuses the `main()` branch that already handles the shadow operations:
`manifest_not_in_packages` refusal, report envelope, and exit code. The new
operation plugs into the same `operation(...)` call signature.

### D5: Release hint text

The two `ReleaseError` strings replace "remove the embedded copy so the file:
dependency wins" with:

> clear it with `python tools/prepare_validation_host.py --clear-embedded-shadow`
> so the file: dependency wins (restore later with `--restore-embedded-shadow`)

The error codes stay the same, so scripts that match on the prefix are
unaffected.

## Risks / Trade-offs

- [The operator forgets the restore, and a later prepare run sees the backup and
  keeps stale originals from long ago] → Accepted. The originals are still the
  correct pre-preparation state, and the run instructions put the restore in
  the teardown step.
- [The hash guard refuses after a harmless reformat] → The refusal names the
  backup path, so the operator can compare and restore by hand.
