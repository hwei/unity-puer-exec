## Why

The repository still relies on a legacy `docs/` workflow for governance, planning, and durable product decisions even though `openspec init` has already been introduced. That leaves two competing process models in the same repository and prevents agents from treating OpenSpec artifacts as the single planning and specification source of truth.

## What Changes

- Replace the legacy `docs/`-centric governance entry path with OpenSpec-owned project guidance and long-lived specs.
- Migrate durable repository workflow rules, validation-host rules, and CLI contract rules into OpenSpec-standard artifacts.
- Reclassify legacy `docs/` files as transitional redirects instead of canonical governance documents.
- Configure `openspec/config.yaml` with repository context and artifact authoring rules that reflect this repository's harness-engineering workflow.

## Capabilities

### New Capabilities
- `repository-governance`: Defines the repository's OpenSpec-first workflow, implementation gating, distillation rules, and retrospective handling.
- `validation-host-integration`: Defines environment resolution, validation-host boundaries, local package injection, and minimal validation expectations for the Unity host workflow.
- `formal-cli-contract`: Defines the durable machine-facing contract for the `unity-puer-exec` CLI surface.

### Modified Capabilities

None.

## Impact

- Affects repository governance entry points in `AGENTS.md`, `ReadMe.md`, and legacy `docs/`.
- Adds long-lived OpenSpec artifacts under `openspec/project.md` and `openspec/specs/`.
- Establishes one active OpenSpec migration change under `openspec/changes/migrate-legacy-governance-to-openspec/`.
