# 0005 Validation Host Local Package Injection

- Date: 2026-03-12
- Status: accepted

## Decision

`T1.2.2.1` uses a clean validation-host baseline plus a local-only manifest injection workflow.

In the current workspace, the preferred clean baseline for validation-host work is commit `e891b5495e8a8ae1950a41d0d85f6314676e13e9`, which is the merge-base of `c3-client-tree2` branch `unity-puer-exec` with `devel/c3-3`.

Validation against the formal package should follow this model:

1. Start from the clean validation-host baseline at that fork point, or from an equivalent clean descendant that still does not carry the formal package as committed host source.
2. Keep product development in `unity-puer-exec/`.
3. Locally edit `c3-client-tree2/Project/Packages/manifest.json` so the host consumes `com.txcombo.unity-puer-exec` from `unity-puer-exec/packages/com.txcombo.unity-puer-exec/`.
4. Prefer the reproducible relative dependency path `file:../../../unity-puer-exec/packages/com.txcombo.unity-puer-exec` from the host `Packages/` directory.
5. Treat that manifest edit as a local validation injection by default and do not commit it as the normal host workflow.
6. Treat `packages-lock.json` as Unity-derived follow-up material, not as a required `T1.2.2.1` deliverable.

The repository-level helper for this local wiring is `tools/prepare_validation_host.py`.

## Rationale

- A clean baseline makes it clear that the host is consuming the product from outside, not still acting as its source-of-truth repository.
- A manifest-only local injection is the narrowest change that proves the host/package boundary without prematurely broadening the task into runtime validation or host cleanup policy.
- Using a reproducible relative path keeps the workflow portable within the shared workspace layout.

## Consequences

- `T1.2.2.1` can be validated statically through manifest rewriting and documentation without requiring immediate Unity import execution.
- `T1.2.2.2` remains responsible for proving that Unity actually imports and runs against the rewired local package.
- Host-local package source cleanup is no longer the primary contract for this task; the clean-baseline plus local-injection workflow is.
