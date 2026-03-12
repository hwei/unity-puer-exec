# 0004 Product Boundary And Naming

- Date: 2026-03-12
- Status: accepted

## Decision

The formal product consists of:

- a Unity package named `com.txcombo.unity-puer-exec`
- a primary CLI named `unity-puer-exec`

The product's public naming should use `UnityPuerExec`, not the current validation-only wording or a `C3`-prefixed product identity.

The Unity-side code should converge on the root namespace `UnityPuerExec`. Validation-only suffixes such as `Validation` are transitional and should be removed from the formal package during migration.

The CLI contract is centered on the `unity-puer-exec` command family. The current `unity-puer-session` entry point is transitional. Its capabilities may continue to exist during the migration period, but the long-lived product surface should be documented and discoverable through `unity-puer-exec`.

Repository responsibilities are:

- `unity-puer-exec/` is the source of truth for the formal Unity package, the formal CLI, and product-facing documentation.
- `c3-client-tree2/` is only the validation host, following [0003-validation-host-operating-model.md](/F:/C3/unity-puer-exec-workspace/unity-puer-exec/docs/decisions/0003-validation-host-operating-model.md).

Current implementation locations are transitional:

- CLI and session code currently live under `.claude/skills/unity-puer-exec/`.
- The Unity package source currently still lives in the validation host and will be migrated into this repository by `T1.2`.

## Rationale

- `com.c3.unity-puer-exec.validation` describes a validation fixture, not a distributable product package.
- A single primary CLI name is easier for both humans and AI agents to discover through `--help` and repository documentation.
- Separating formal product naming from temporary storage locations allows migration work to proceed without redefining the product each time code moves.

## Consequences

- Repository-facing docs should describe the product in terms of `com.txcombo.unity-puer-exec`, `UnityPuerExec`, and `unity-puer-exec`.
- Migration work must rename Unity package metadata, namespaces, and assembly names away from `Validation`.
- CLI formalization work should consolidate or clearly subordinate transitional companion entry points under the primary `unity-puer-exec` surface.
