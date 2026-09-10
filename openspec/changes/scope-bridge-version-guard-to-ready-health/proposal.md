## Why

`enforce-cli-version-compatibility` made an omitted `bridge_version` a terminal `version_mismatch`, intending to catch a ready, unversioned old bridge. `project-control-endpoint` only requires `bridge_version` on **ready** health, and the compiling `/health` stub omits it by construction. After a C# edit, `exec --refresh-before-exec` (and other commands that extra-probe `/health`) therefore refuse with `guard: bridge_version_unknown` while Unity is compiling or reconnecting — even though refresh already ran. A 2026-09-10 Workbuddy session on `c3-client-tree5` reproduced this and workarounded it by ignoring the refusal and retrying without `--refresh-before-exec`, which the version contract forbids as a bypass.

## What Changes

- Scope the bridge-version guard so a missing `bridge_version` is a mismatch only on an identity-bearing **ready** health payload. A `compiling` or `not_available` payload that omits version is "not observable yet", not mixed installation.
- Require compiling (and other non-ready) health responses to include `bridge_version` when the Editor assembly belongs to an installed package, so a matching pair can keep working through the compile window even if a caller probes during compile.
- Keep a genuine version disagreement terminal even on a compiling payload that *does* carry `bridge_version`.
- Keep D5 for ready services: a ready health that omits `bridge_version` remains `bridge_version_unknown`.
- No bypass flag. Callers must not be taught to ignore `version_mismatch`.
- Out of scope: empty HTTP body / `Expecting value: line 1 column 1` disconnects during domain reload. That is a sibling reload-window transport failure, not this guard.

## Capabilities

### New Capabilities

- None. This tightens an existing contract; it does not add a new product surface.

### Modified Capabilities

- `cli-version-compatibility`: the "unavailable counterpart version is a mismatch" requirement is scoped to ready health. Pre-ready health that omits `bridge_version` SHALL NOT produce `version_mismatch`. A compiling payload that carries a disagreeing `bridge_version` still SHALL.
- `project-control-endpoint`: non-ready health (`compiling`, and `not_available` when the service is bound) SHALL include `bridge_version` when it is known from package metadata, instead of emitting a stub that drops identity.

## Impact

- `packages/com.txcombo.unity-puer-exec/Editor/UnityPuerExecProtocol.cs`: compiling / not_available JSON includes `bridge_version` when known.
- `cli/python/cli_version.py` and `cli/python/unity_session.py`: extra-probe and owned-endpoint guards treat missing version as mismatch only for ready payloads (`require_version` follows status).
- `cli/python/unity_puer_exec_runtime.py`: `_base_url_bridge_guard` uses the same ready-only missing-version rule so `--base-url wait-for-compile` / `exec --refresh-before-exec` do not refuse mid-compile.
- `tests/test_cli_version.py` (and related session tests): compiling stub without version is not a refusal; ready without version still is; compiling with a wrong version still is.
- Agents driving the C# compile loop can use `--refresh-before-exec` without a false mixed-install refusal. Real mixed installs on a ready endpoint still fail with exit 24.
