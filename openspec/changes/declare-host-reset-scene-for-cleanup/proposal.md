# Proposal

## Why

The validation harness only cleans what the repository declares safe to remove:
`tools/cleanup_validation_host.py` limits itself to `DECLARED_VALIDATION_TEMP_ROOTS`
(`Assets/__AgentValidation`, `Assets/__codex_validation_temp`, `Assets/CodexValidation`). The
real-host suite also creates `Assets/__codex_host_reset/Baseline.unity` — `_restore_active_scene`
writes it through the Editor so the next case does not inherit a pathless scene — and that root is
not declared.

So every real-host run leaves three untracked files in the host project
(`__codex_host_reset/`, `Baseline.unity`, and two `.meta` files) that no cleanup step will ever
remove. The host's version-control status is dirty after a run and stays dirty, which is how
`fix-unchanged-content-refresh-loop` found it: restoring the host to the state it was found in meant
deleting that residue by hand, because the repository-owned cleanup tool refuses — correctly — to
touch a path outside its declared inventory.

The existing cleanup requirements are not wrong; they are just not covering this asset. The
inventory and the suite's creations have no mechanism that keeps them in agreement.

## What Changes

- `Assets/__codex_host_reset` joins `DECLARED_VALIDATION_TEMP_ROOTS`, so the harness removes the
  host-reset scene and its metadata after successful and failed runs alike, under the rules that
  already govern the other declared roots.
- A repository-level guard cross-references the repository-owned asset roots the real-host suite
  creates against the declared inventory and fails when one is undeclared, so the next suite-created
  asset cannot reproduce this gap silently.
- The refusal behaviour for a path outside the inventory is unchanged. Declaring the root is what
  makes it cleanable; it does not widen what the tool will touch on a caller's say-so.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `validation-temp-asset-cleanup`: adds a requirement that the declared inventory covers every
  repository-owned asset the real-host suite creates in the host, and that the agreement is enforced
  by a repository test rather than left to memory. The four existing requirements — cleanup scope,
  cleanup on success and failure, verified and recorded outcome, and never removing an asset the live
  Editor still references — are unchanged.

## Impact

- **Tooling**: `tools/cleanup_validation_host.py` — one entry added to `DECLARED_VALIDATION_TEMP_ROOTS`.
- **Tests**: `tests/test_cleanup_validation_host_tool.py` gains the inventory-versus-suite guard;
  `tests/test_real_host_reset.py` is unaffected because it asserts the scene path the suite writes,
  not the cleanup inventory.
- **Hosts**: a host carrying residue from an earlier run is cleaned on the next run. Residue already
  deleted by hand needs nothing.
- **Product**: none.
- **Upstream**: inherits the inventory-scoped cleanup contract as landed; this change adds one member
  to the inventory and a guard, and does not revisit the "declared inventory only" rule that makes
  the tool safe to point at someone else's Unity project.
