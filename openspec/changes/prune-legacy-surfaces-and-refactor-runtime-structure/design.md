## Context

The repository already separates product source, validation tooling, tests, and OpenSpec artifacts cleanly at the top level. The main maintainability pressure is inside the runtime implementation:

- `cli/python/unity_session.py` combines environment resolution, session artifact persistence, process control, health polling, and log observation.
- `cli/python/unity_puer_exec.py` combines parser construction, command dispatch, payload shaping, and help-entry special cases.
- `cli/python/help_surface.py` maintains a parallel command-description surface beside the parser definitions.
- `packages/com.txcombo.unity-puer-exec/Editor/UnityPuerExecServer.cs` combines HTTP handling, job state, JS wrapping, bridge methods, transitional batch helpers, and compile-trigger compatibility logic.

The change also needs to deal with compatibility leftovers deliberately. Some surfaces are still repository-owned compatibility paths, while others appear to be dead transitional code. This work should prune confirmed-dead code first, isolate compatibility shims second, and only then redistribute the remaining runtime code into clearer modules.

Repository inspection during apply has already separated the first buckets:

- Confirmed-dead candidates: `UnityPuerExecBatch`, `BuildStringArrayJson`, and the unused `--keep-unity` alias flag.
- Explicit shim candidates pending later isolation work: `unity-puer-session` and the compile-trigger bridge path exposed through `TriggerValidationCompile`.

## Goals / Non-Goals

**Goals:**

- Remove confirmed-dead transitional runtime code before moving long-lived modules around it.
- Keep compatibility-only entry points explicit, thin, and easy to remove later.
- Split Python runtime responsibilities so CLI command routing, session/runtime control, and help metadata stop cohabiting in oversized files.
- Split Unity Editor runtime responsibilities so server lifecycle, job state, and bridge helpers can evolve independently.
- Preserve the formal `unity-puer-exec` contract and current real-host validation workflow.

**Non-Goals:**

- Redesign the formal CLI command tree or machine-readable payload contract.
- Add new product-facing execution features.
- Change the external validation-host boundary or replace the current real-host regression path.
- Remove a compatibility surface whose external usage is still unverified.

## Decisions

### Decision: Prune confirmed-dead code before structural moves

The implementation will remove repository-owned code only when repository evidence shows that the surface is unused and not part of a documented authoritative contract. This avoids wasting refactor effort on dead scaffolding and reduces the number of moving parts during later file splits.

Alternative considered: refactor first and prune later. Rejected because that would preserve migration residue and force maintainers to carry dead code through the new structure.

### Decision: Keep compatibility surfaces, but isolate them as shims

Compatibility-only paths such as `unity-puer-session` will remain allowed only as thin adapters to the formal runtime. They must not gain new business logic, new behavioral branches, or their own divergent help/contract story.

Alternative considered: remove all compatibility surfaces in the same change. Rejected because repository-local evidence is enough to identify likely removal candidates, but not necessarily enough to prove that all external callers have already migrated.

### Decision: Centralize command metadata and thin the CLI entry module

The Python CLI should move toward a structure where command metadata, parser registration, help rendering, and command handlers are coordinated from shared definitions rather than duplicated in multiple large files. `unity_puer_exec.py` should remain a thin entry module that wires together parser setup and command execution.

Alternative considered: keep the current parser/help split and only move helper functions around. Rejected because it would leave the most important maintenance problem intact: command truth spread across multiple authoritative-looking files.

### Decision: Split session/runtime control by concern, not by call site

`unity_session.py` should be decomposed into modules aligned to stable responsibilities, such as environment/project-path resolution, session artifact and log-source resolution, process control, and health/log observation. A small facade may remain for compatibility with current imports and tests during migration.

Alternative considered: split by command (`ready`, `observe`, `stop`). Rejected because the current complexity is driven more by runtime concern overlap than by the CLI command names.

### Decision: Split Unity Editor runtime into server, bridge, and transitional compatibility areas

The Unity package should separate HTTP server lifecycle and request handling, job tracking, script wrapping, and bridge exposure. Transitional compile-trigger and batch-helper code should either be removed or confined to clearly marked compatibility files so the main runtime no longer presents them as central logic.

Alternative considered: keep one editor file and only add region markers/comments. Rejected because the issue is not discoverability alone; it is ownership and change coupling.

## Risks / Trade-offs

- [Risk] A supposedly dead helper may still be used by a repository-external validation habit or manual workflow. -> Mitigation: remove only surfaces with no repository callers and no authoritative documentation dependency; keep uncertain surfaces as isolated shims first.
- [Risk] Splitting parser/help/session code may break tests that import old module-level names directly. -> Mitigation: preserve a thin compatibility facade during the migration and update tests alongside the refactor.
- [Risk] Refactoring Unity Editor runtime may accidentally change request timing or logging behavior. -> Mitigation: preserve the external `/health` and `/exec` behavior, and rerun package-layout and real-host relevant validation after restructuring.
- [Risk] Internal cleanup work may silently widen into behavior redesign. -> Mitigation: bind the implementation to the unchanged formal CLI contract and treat behavior changes as out of scope unless a follow-up change is opened.

## Migration Plan

1. Identify and delete confirmed-dead transitional code with focused tests updated in the same step.
2. Move compatibility-only surfaces into clearly marked shim locations or patterns, keeping behavior thin and unchanged.
3. Extract shared CLI metadata and handler boundaries so `unity_puer_exec.py` becomes a small entry module.
4. Extract session/runtime helpers behind a compatibility facade and update tests to target the new module seams.
5. Split Unity Editor runtime into smaller files while preserving formal response and bridge behavior.
6. Run repository tests and targeted host-validation evidence needed to prove no CLI-contract regression.

## Open Questions

- Is any repository-external automation still invoking `UnityPuerExecBatch`, or can it be deleted outright?
- Should the compatibility shim for `unity-puer-session` remain in its current path or move into an explicitly named `compat` module during the refactor?
- How far should help generation be centralized in this change versus staged into a follow-up after the runtime split lands?
