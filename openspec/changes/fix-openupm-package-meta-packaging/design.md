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

### Decision: Put the requirement in durable package and release truth, not only in ad hoc release notes

The missing `.meta` issue is a durable package contract problem, so it belongs in `cli-binary-packaging` and `openupm-release-pipeline` rather than only in one-off validation notes.

### Decision: Validate the publishable tree before treating a release as healthy

The release path should fail or at least report clearly when Unity-imported package paths are missing committed `.meta` files.

### Decision: Treat committed `.meta` siblings as part of the publishable package tree

The release workflow's "clean package tree" rule should exclude development-only content, but it should not strip committed `.meta` siblings for Unity-imported assets such as `Editor`, `package.json`, or `LICENSE`. Those metadata files are part of the publishable package contract even though they are not hand-authored runtime sources.

## Risks / Trade-offs

- [Risk] Validation may over-constrain intentionally hidden package content. Mitigation: scope the rule explicitly to Unity-imported package assets and exclude `CLI~/`.
