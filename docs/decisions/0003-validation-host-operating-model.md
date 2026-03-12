# 0003 Validation Host Operating Model

- Date: 2026-03-12
- Status: accepted

## Decision

`unity-puer-exec/` is the only productized development repository for the formal Unity package and the formal CLI.

`c3-client-tree2/` is the validation host. It exists to run and verify `unity-puer-exec` against a real Unity project, not to carry the product's long-lived source of truth.

Validation work should follow these rules:

1. The validation host should be checked out to a baseline branch that does not already contain the formal `unity-puer-exec` package as committed host source.
2. The formal package and CLI should be developed and versioned in `unity-puer-exec/`.
3. Validation should prefer local injection methods such as local package references or other local-only host edits.
4. Host-local edits made only to mount or exercise `unity-puer-exec` should remain uncommitted by default.
5. Changes to the validation host itself should be committed only when the host has its own independent need, not as the normal path for shipping `unity-puer-exec`.

## Rationale

- Product code and validation fixture code have different lifecycles and should not share the same source-of-truth repository.
- A baseline host branch without embedded product code makes it easier to prove that installation and validation flows work from the outside.
- Keeping test injection local by default reduces the risk that temporary harness changes are mistaken for product deliverables.

## Consequences

- Repository docs and plans must explicitly distinguish the productized repository from the validation host.
- Migration work should remove the current package from the validation host as a committed product location.
- E2E validation must document how the host is prepared locally for testing without redefining the host as the product repository.
