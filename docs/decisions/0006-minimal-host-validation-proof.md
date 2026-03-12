# T1.2.2.2 Minimal Host Validation Proof

## Status

Accepted

## Context

`T1.2.2.2` needed a runtime proof that the validation host can consume the formal local package `com.txcombo.unity-puer-exec` through manifest injection and execute Unity code from that package, rather than only passing a static file inspection.

The validation host operating model and local package injection path were already defined in:

- `docs/decisions/0003-validation-host-operating-model.md`
- `docs/decisions/0005-validation-host-local-package-injection.md`

## Decision

The minimal runtime proof for the rewired validation host is:

1. Move the validation host worktree to commit `e891b5495e8a8ae1950a41d0d85f6314676e13e9`.
2. Rewrite `../c3-client-tree2/Project/Packages/manifest.json` with:
   - `python tools/prepare_validation_host.py --manifest-path ../c3-client-tree2/Project/Packages/manifest.json`
3. Launch Unity 2022.3.62f2 in batch mode against `../c3-client-tree2/Project` with:
   - `-executeMethod UnityPuerExec.UnityPuerExecBatch.PrintHealth`
   - `-nographics`
   - `-logFile <explicit local log path>`

The run is considered successful only when the explicit Unity log contains all of:

- `[UnityPuerExecBatch] health-check-start`
- `[UnityPuerExecBatch] port=...`
- `[UnityPuerExecBatch] health-check-end`

## Evidence

The `T1.2.2.2` run used:

- host baseline commit: `e891b5495e8a8ae1950a41d0d85f6314676e13e9`
- host project: `../c3-client-tree2/Project`
- explicit log: `.tmp/t1.2.2.2-unity.log`
- execute method: `UnityPuerExec.UnityPuerExecBatch.PrintHealth`

The explicit Unity log showed the formal package as a local package:

- `com.txcombo.unity-puer-exec@file:F:\C3\unity-puer-exec-workspace\unity-puer-exec\packages\com.txcombo.unity-puer-exec`

The explicit Unity log also showed the validated runtime markers from:

- `packages/com.txcombo.unity-puer-exec/Editor/UnityPuerExecServer.cs`

Observed values from the successful run:

- `[UnityPuerExecBatch] health-check-start`
- `[UnityPuerExecBatch] port=55231`
- `[UnityPuerExecBatch] health-check-end`

## Consequences

- `T1.2.2.2` is satisfied: the validation host has consumed the formal local package and executed Unity-side code from it.
- The current minimal proof remains an agent-operated validation step, not yet the normalized repo-level E2E entry.
- The validation host may rewrite `packages-lock.json` during cold startup, but that remains a host-local artifact and is not a required committed output of this task.
- The baseline host still emits project-local import issues during cold startup, including ShaderGraph-related exceptions and missing sub-graph validation errors. These did not block the `UnityPuerExecBatch.PrintHealth` proof path, but they remain relevant caveats when interpreting cold-start logs.
- The validated command path used an explicit `-logFile` and manual process observation. More automated orchestration can be introduced later through CLI formalization or repo-level validation tasks.
