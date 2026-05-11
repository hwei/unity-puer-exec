## Why

Archive-readiness host validation for `improve-cache-staleness-detection-and-examples` found that a validation project can have `Packages/manifest.json` rewritten to the repository-local package while Unity still loads an embedded `Project/Packages/com.txcombo.unity-puer-exec` copy. That makes real-host evidence unreliable because the run may exercise stale host source instead of the change under validation.

## What Changes

- Add validation-host requirements that repository-owned wiring checks detect or warn about embedded package shadowing.
- Update real-host run guidance so contributors know manifest rewiring alone is not enough when an embedded package directory is present.
- Extend `tools/prepare_validation_host.py` to report embedded package shadowing in its machine-readable output.
- Add unit coverage for the shadowing detection path.

## Capabilities

### New Capabilities
- none

### Modified Capabilities
- `validation-host-integration`: Require repository-owned validation-host preparation to surface embedded package copies that can shadow the intended local package injection.

## Impact

- `openspec/specs/validation-host-integration/spec.md`
- `openspec/specs/validation-host-integration/how-to-run.md`
- `tools/prepare_validation_host.py`
- `tests/test_prepare_validation_host_tool.py`
