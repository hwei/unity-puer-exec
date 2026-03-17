## Why

The repository still keeps pre-OpenSpec decision documents in the working tree, which makes it look like there are two parallel durable truth systems. Those files should be removed entirely so OpenSpec specs remain the only canonical source for active requirements and git history remains the only legacy record.

## What Changes

- Delete the remaining legacy decision documents from the working tree.
- Remove repository guidance that still presents `docs/decisions/` as a compatibility layer.
- Keep legacy decision history only through git history and archived OpenSpec changes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: Clarify that once governance has migrated into OpenSpec, legacy decision files are removed instead of being kept as compatibility artifacts.

## Impact

- Removes `docs/decisions/` and `docs/legacy-decisions/` from the working tree.
- Tightens the repository's OpenSpec-first governance boundary.
