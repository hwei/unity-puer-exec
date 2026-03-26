## Why

ReadMe.md is the first file users see when evaluating or adopting unity-puer-exec, but it currently contains only internal developer governance content (product boundary definitions, OpenSpec entry points, test layer descriptions). Users—Unity developers wanting to integrate the package or CLI—have no installation path, no usage description, and no requirements summary. This needs to be fixed before any public release effort can proceed.

## What Changes

- **ReadMe.md** is rewritten as a user-facing document: product summary, requirements, installation, and basic usage.
- **Product boundary section** (lines 5–13 of current ReadMe.md) is retired or consolidated into AGENTS.md contributor guidance; most of it is already implicit in AGENTS.md's environment setup and the OpenSpec config context.
- **"快速入口" quick-links section** (OpenSpec paths, test command) is retired from ReadMe.md; AGENTS.md already carries the canonical OpenSpec entry-point list.
- **Test layering, real-host regression, result interpretation sections** are migrated into AGENTS.md as a new contributor testing section, since they describe the contributor workflow and are not relevant to end users.
- **Directory overview** is retired from ReadMe.md; AGENTS.md and openspec/config.yaml already describe the layout for contributors.

No product behavior changes. No spec-level requirements change.

## Capabilities

### New Capabilities

*(none — this is a documentation refactor)*

### Modified Capabilities

*(none — no durable spec requirements change)*

## Impact

- `ReadMe.md`: complete rewrite
- `AGENTS.md`: new "Testing" section appended with migrated content (test layering, real-host regression, result interpretation)
- All other files: unchanged
