# Spec Delta

## ADDED Requirements

### Requirement: Validation host manifest wiring is reversible

When preparation tooling first rewrites a host's `Packages/manifest.json`, it SHALL save the original `manifest.json` and, if present, `packages-lock.json` into a host-local backup outside `Packages/`. A restore operation SHALL move both back. Neither direction SHALL delete anything or perform a version-control operation on the host, and both SHALL report machine-readably the action taken and the backup path.

#### Scenario: First rewrite saves the originals

- **WHEN** preparation rewrites a host manifest that has no existing manifest backup
- **THEN** the original `manifest.json` and `packages-lock.json` are saved into the host-local backup before the rewrite
- **AND** the report names the backup path

#### Scenario: A repeated rewrite keeps the first backup

- **WHEN** preparation rewrites a host manifest that already has a manifest backup
- **THEN** the existing backup is left untouched, so it still holds the pre-preparation originals

#### Scenario: Restore returns the host to its pre-preparation files

- **WHEN** a contributor asks preparation to restore the manifest
- **AND** a manifest backup exists
- **THEN** the tool moves the saved `manifest.json` and `packages-lock.json` back into `Packages/`
- **AND** the host's version-control status for those files matches what it was before the first preparation
- **AND** it reports the restored status

#### Scenario: Restore with nothing to restore is unchanged

- **WHEN** a contributor asks to restore the manifest
- **AND** no manifest backup exists
- **THEN** the tool reports an unchanged status rather than failing
- **AND** it writes nothing

### Requirement: Manifest restore refuses to overwrite foreign edits

The manifest restore SHALL refuse when the current `manifest.json` differs from the content preparation last wrote, naming the reason, so that edits made after preparation are never silently discarded.

#### Scenario: Manifest edited after preparation

- **WHEN** a contributor asks to restore the manifest
- **AND** `manifest.json` no longer matches the content preparation last wrote
- **THEN** the tool refuses and states that the manifest changed since preparation
- **AND** it moves nothing

#### Scenario: Regenerated lock file does not block restore

- **WHEN** Unity has regenerated `packages-lock.json` after preparation
- **AND** `manifest.json` still matches what preparation wrote
- **THEN** the restore proceeds and replaces the regenerated lock file with the saved original

### Requirement: Manifest restore follows the shadow-switch safety rules

The manifest restore SHALL refuse while the host is not free, decided from the same project-local evidence that shadow switching uses, and SHALL honour preview mode by reporting what it would move without writing.

#### Scenario: A live Editor blocks the restore

- **WHEN** a contributor asks to restore the manifest
- **AND** the host project's lockfile is held or its Editor has published a control endpoint
- **THEN** the tool refuses, names the evidence, and moves nothing

#### Scenario: Preview reports the intended restore

- **WHEN** a contributor asks to restore the manifest in preview mode
- **THEN** the tool reports the files it would move and the backup path
- **AND** it writes nothing and reports the preview status
