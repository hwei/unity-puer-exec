## Context

The validation host is external to this repository, but repository-owned tooling prepares it for real-host evidence by rewriting `Packages/manifest.json` to consume the local `packages/com.txcombo.unity-puer-exec` package. The recent staleness validation showed that a host can still contain an embedded `Project/Packages/com.txcombo.unity-puer-exec` directory. Unity gives embedded packages local precedence, so the manifest rewrite can appear correct while the editor imports and executes a stale package copy.

## Goals / Non-Goals

**Goals:**
- Make this shadowing condition visible before contributors trust real-host validation evidence.
- Preserve the existing manifest rewrite behavior.
- Keep the check machine-readable so scripts and agents can branch on it.
- Document the human validation precaution next to the real-host run instructions.

**Non-Goals:**
- Automatically delete or mutate the validation host's embedded package directory.
- Change Unity package resolution behavior.
- Make all real-host tests depend on a specific external host repository layout.

## Decisions

### 1. Report shadowing from `prepare_validation_host.py`

`prepare_validation_host.py` is the right first guard because it is already the documented wiring step and runs before real-host validation. It will inspect `<Project>/Packages/com.txcombo.unity-puer-exec` when a project path is available and include `embedded_package_shadowing` plus `embedded_package_path` in the JSON output.

Alternative considered: only document the issue. Rejected because the failure mode is easy to miss; the manifest output can say `unchanged` even while Unity is loading the embedded directory.

### 2. Warn rather than fail

The first implementation reports a warning instead of failing. Some host states may intentionally validate an embedded package. The durable requirement is that repository-owned local-package validation evidence cannot silently ignore the warning.

Alternative considered: fail-fast by default. Rejected because it could break existing host workflows and because the repository does not own the external host's source-control policy.

### 3. Keep cleanup manual

The helper will not delete or move the embedded package. Removing a package directory in an external Unity project is destructive enough that a tool should not do it as a side effect of preparation.

## Risks / Trade-offs

- [Risk] Contributors may ignore a warning and still trust stale evidence. -> Mitigation: Document the warning in `how-to-run.md` and include a stable JSON field for automation.
- [Risk] A host intentionally validating its embedded copy will see noise. -> Mitigation: The result is a warning, not a hard failure.
- [Risk] Path comparison can be fooled by symlinks or junctions. -> Mitigation: Resolve paths before comparing; if the path is distinct from the repository package root, report the condition.
