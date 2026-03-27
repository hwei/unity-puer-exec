## Why

The OpenUPM real-host validation exposed an immutable-package warning: `Packages/com.txcombo.unity-puer-exec/Editor` lacked a committed `.meta` file in the published package tree. Even though the representative workflow still succeeded, Unity reported that the asset would be ignored, which makes the published package look structurally unsound.

## What Changes

- Ensure the publishable package tree includes the required committed `.meta` files for Unity-imported package assets outside `CLI~/`.
- Add repository-owned packaging validation so a future OpenUPM release cannot silently omit required Unity package metadata.
- Clarify the package-layout contract for publishable package assets versus intentionally hidden `CLI~/` contents.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `cli-binary-packaging`: the package layout requirements expand beyond `CLI~/` placement to require committed Unity `.meta` coverage for Unity-imported package assets in the published package tree.
- `openupm-release-pipeline`: the assembled publish tree must preserve the committed `.meta` siblings required by Unity-imported package assets instead of copying only the primary asset files.

## Impact

- [`packages/com.txcombo.unity-puer-exec/`](F:/C3/unity-puer-exec-workspace/unity-puer-exec/packages/com.txcombo.unity-puer-exec)
- Packaging validation around the publishable OpenUPM tree
- [`openspec/specs/cli-binary-packaging/spec.md`](F:/C3/unity-puer-exec-workspace/unity-puer-exec/openspec/specs/cli-binary-packaging/spec.md)
- [`openspec/specs/openupm-release-pipeline/spec.md`](F:/C3/unity-puer-exec-workspace/unity-puer-exec/openspec/specs/openupm-release-pipeline/spec.md)
