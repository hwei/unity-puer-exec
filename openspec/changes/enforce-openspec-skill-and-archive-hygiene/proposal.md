## Why

The repository now has evidence that a new agent session can reach for manual directory operations instead of the intended OpenSpec workflow, which makes archive state easier to corrupt. The visible symptom is an archived change that still has an empty active-directory placeholder, causing active planning scans to show a stale change entry.

## What Changes

- Add explicit repository guidance that agents should prefer the installed OpenSpec skills and official `openspec` commands for propose/apply/archive work instead of hand-editing `openspec/changes/` directories.
- Document the archive hygiene rule that active change paths should disappear after archive unless a human is intentionally repairing abnormal state.
- Manually remove the stale empty active-directory placeholder for `validate-help-only-agent-cli-discoverability`.
- Re-check active planning views after the cleanup so the repository no longer shows the archived change as active work.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `repository-governance`: agent workflow guidance should explicitly favor OpenSpec skills and official archive commands over manual directory manipulation.

## Impact

- Affects repository workflow guidance in `AGENTS.md` and `openspec/project.md`.
- Affects durable governance requirements for archive hygiene.
- Cleans up one existing planning-surface inconsistency under `openspec/changes/`.
