## Why

`tools/prepare_validation_host.py` detects an embedded package that shadows the repository-local package by looking for a **directory named** `com.txcombo.unity-puer-exec`:

```python
embedded_package_path = Path(manifest_path).parent / FORMAL_PACKAGE_NAME
if not embedded_package_path.exists():
    return False, None
```

Unity does not work that way. Any directory under `Packages/` containing a `package.json` is loaded as an embedded package, and its identity comes from that file's `name` field — the directory name is irrelevant. The tool and Unity therefore disagree about what an embedded package is, and the disagreement produces a **false negative**: a shadowing copy under any other directory name is reported as clean while Unity keeps loading it.

This was hit directly on 2026-07-23 while validating `enforce-cli-version-compatibility`. The validation host carried an embedded v0.6.0 copy of the package. It was renamed to `com.txcombo.unity-puer-exec.bak` to clear the shadow, and the tool then reported `embedded_package_shadowing: false` — but `PackageInfo.FindForAssembly` inside the running Editor still resolved `version 0.6.0` from `resolvedPath: …/Packages/com.txcombo.unity-puer-exec.bak`, with `source: Embedded`. The host only picked up the repository package after the directory was moved out of `Packages/` entirely.

The durable requirement encodes the same wrong model: it is written in terms of "an embedded `Packages/com.txcombo.unity-puer-exec` directory". So the spec, the tool, and the operator's mental model all share a defect that Unity does not.

A false negative here is worse than no check. The report exists so a contributor can decide whether a real-host run is valid evidence for repository-local package changes; a confident "clean" that is wrong converts a safety check into a source of misplaced trust.

## What Changes

- Detect embedded shadowing by the declared package identity rather than the directory name: scan the immediate children of `Packages/` for a `package.json` whose `name` is the formal package name, regardless of what the directory is called.
- Report the actual shadowing directory path so a contributor can act on it without searching.
- Report every shadowing directory when more than one qualifies, rather than only the first, because a partially cleaned host is exactly the state that produces confusing results.
- Continue treating an embedded path that resolves to the repository-local package root as not shadowing, which is the existing intentional-injection case.
- Restate the durable requirement in terms of declared package identity, so the spec stops describing a rule Unity does not follow.
- Record in the real-host run instructions that renaming an embedded package directory does not clear the shadow and that the directory must be moved out of `Packages/`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `validation-host-integration`: the embedded-package-shadowing requirement is restated to key on the declared package name inside `package.json` rather than on the directory name, and to report all shadowing directories.

## Impact

- `tools/prepare_validation_host.py`: `detect_embedded_package_shadowing` reads candidate `package.json` files instead of testing one fixed directory path; the reported result gains the ability to name more than one path.
- `tests/test_prepare_validation_host_tool.py`: coverage for a renamed shadowing directory, multiple shadowing directories, an unrelated package directory that must not be flagged, and a malformed or missing `package.json` that must not crash the scan.
- `openspec/specs/validation-host-integration/spec.md` via delta spec.
- `openspec/specs/validation-host-integration/how-to-run.md`: the rename-is-not-enough note.
- Contributors whose hosts report clean today may start reporting shadowing. That is the correction, not a regression.
