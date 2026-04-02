## Context

The upstream runtime-structure cleanup change on 2026-03-18 deliberately moved compile-trigger behavior out of `UnityPuerExecServer.cs` and into `UnityPuerExecCompileCompat.cs` instead of deleting it immediately. That design explicitly treated `TriggerValidationCompile` as an uncertain shim candidate: isolate first, then remove later if no authoritative dependency remains.

Subsequent repository changes replaced the product-facing compile/refresh path with `exec --refresh-before-exec`, implemented through direct `AssetDatabase.Refresh()` execution inside the normal `exec` lifecycle. The remaining compile-compat file now contributes two things only:

- a dead menu item under `Tools/Unity Puer Exec/Trigger Package Compile`
- a public bridge method retained solely as historical compatibility residue

Current repository evidence shows no repo-local callers outside the shim file itself and one package-layout test that exists only to enforce the shim's continued presence.

## Goals / Non-Goals

**Goals:**

- Remove the dead compile-compat shim from the Unity package.
- Preserve the formal refresh and execution workflow centered on `exec --refresh-before-exec`.
- Update tests and durable OpenSpec guidance so the repository no longer treats the shim as expected package structure.

**Non-Goals:**

- Redesign the Unity-side refresh workflow or the `reset-jsenv` flow.
- Introduce a new compatibility layer to replace the compile-compat shim.
- Guarantee compatibility for unknown repository-external manual workflows that were never documented as product contract.

## Decisions

### Decision: Remove the entire compile-compat file instead of only deleting the menu item

Repository inspection found no remaining repo-local use of `UnityPuerExecCompileCompatBridge.TriggerValidationCompile(...)`; preserving the public bridge would therefore keep a dead entry point alive without any product contract to justify it. Deleting only the menu would reduce the visible surface but still leave an undocumented bridge method inside the package.

Alternative considered: remove only `[MenuItem(...)]` and keep the bridge method. Rejected because the remaining bridge would still be dead package API residue, and the repository already has a formal refresh path.

### Decision: Treat `exec --refresh-before-exec` as the only authoritative refresh workflow

The CLI runtime already performs refresh through the normal exec lifecycle by running `AssetDatabase.Refresh()` and then continuing with the same request handling model. That path is the one referenced by current help text, tests, and durable specs. The design therefore removes compile-compat without replacing it.

Alternative considered: retarget the bridge implementation to call into the refresh workflow. Rejected because it would preserve an undocumented compatibility surface instead of deleting confirmed-dead code.

### Decision: Update runtime-structure-hygiene with an explicit follow-up cleanup rule

The repository already says confirmed-dead transitional code should be removed, but this case benefits from a more explicit rule for isolated shims that were retained temporarily during an earlier refactor. Adding that rule documents why deleting a previously isolated shim is expected follow-up maintenance rather than opportunistic cleanup.

Alternative considered: rely on the existing generic dead-code rule without a spec delta. Rejected because this change is explicitly about moving an isolated shim from "temporarily retained" to "confirmed dead", which is worth capturing as durable guidance.

## Risks / Trade-offs

- [Risk] An undocumented repository-external maintainer habit may still invoke `UnityPuerExecCompileCompatBridge.TriggerValidationCompile(...)`. -> Mitigation: record in proposal/spec/design that no formal contract promises this surface, and validate that documented workflows continue to pass without it.
- [Risk] Package-layout tests may overfit to the previous file list and fail after removal. -> Mitigation: update the test to assert the absence of compile-compat-specific structure and preserve checks for the formal runtime files.
- [Risk] Cleanup could be mistaken for refresh workflow redesign. -> Mitigation: keep scope tight and revalidate only the existing `--refresh-before-exec` path plus package layout expectations.

## Migration Plan

1. Delete `UnityPuerExecCompileCompat.cs` and its `.meta` file from the Unity package.
2. Update package-layout tests so they no longer require the compile-compat file or bridge symbol to exist.
3. Run repository tests covering package layout and CLI refresh behavior.
4. Close out with an explicit note that no new authoritative replacement surface was introduced.

Rollback is straightforward: restore the deleted shim file and revert the corresponding test/spec updates if a documented dependency is discovered during validation.

## Open Questions

- Is there any maintained external automation outside this repository that still reflects on `UnityPuerExecCompileCompatBridge` directly?
- Should the closeout note recommend a release-note mention even though the shim was never documented as formal surface?
