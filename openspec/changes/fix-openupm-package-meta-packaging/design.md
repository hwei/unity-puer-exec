## Context

The follow-up validation change `validate-openupm-real-host-usability` recorded a Unity warning from the published OpenUPM package: a package path under `Packages/com.txcombo.unity-puer-exec/Editor` had no `.meta` file even though it lived in an immutable package folder. That warning indicates a packaging hole rather than a host-only anomaly.

## Goals / Non-Goals

**Goals:**
- Make the published package tree structurally valid for Unity-imported assets.
- Prevent future releases from omitting required `.meta` files unnoticed.

**Non-Goals:**
- Change the intentionally hidden `CLI~/` rule.
- Redesign the package layout beyond what is needed to restore correct metadata coverage.

## Decisions

### Decision: Put the requirement in package-layout truth, not only in ad hoc release notes

The missing `.meta` issue is a durable package contract problem, so it belongs in `cli-binary-packaging` rather than only in one-off validation notes.

### Decision: Validate the publishable tree before treating a release as healthy

The release path should fail or at least report clearly when Unity-imported package paths are missing committed `.meta` files.

## Risks / Trade-offs

- [Risk] Validation may over-constrain intentionally hidden package content. Mitigation: scope the rule explicitly to Unity-imported package assets and exclude `CLI~/`.
