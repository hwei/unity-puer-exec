## Why

The repository still carries a top-level `docs/` directory that no longer contains canonical information. Even as redirects, those files create avoidable ambiguity for AI agents and humans because they imply a second navigation path beside OpenSpec.

## What Changes

- Delete the remaining legacy `docs/` directory from the working tree.
- Update repository guidance so OpenSpec is described as the only current governance and specification surface.
- Record the deletion in an OpenSpec change so the intent remains reviewable.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: Clarify that legacy docs do not remain in the working tree after migration to OpenSpec.

## Impact

- Removes `docs/` from the repository working tree.
- Tightens the repository's OpenSpec-first entry model for agents and humans.
