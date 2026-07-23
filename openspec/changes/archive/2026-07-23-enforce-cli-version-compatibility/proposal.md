## Why

An external agent validation session on 2026-07-23 produced a feedback report whose three most concrete "missing feature" claims were wrong: the agent ran the v0.6.0 CLI executable while the repository was at v0.7.0, and reported `get-log-briefs --full-text`, `get-log-briefs --indexes`, and the global `--response-file` as absent capabilities. All three had shipped in v0.7.0. Nothing in the product could have revealed the mismatch — the executable carries no version string, no response field names the build, `--version` is not accepted, and the v0.6.0 binary sat in a `CLI~/` directory immediately beside a `package.json` declaring `0.7.0`, so the agent's reasonable version inference was actively misled. The agent itself flagged the suspicion ("`CLI~/` is untracked, so this cannot prove the exe was built from HEAD") but had no mechanism to confirm it.

The CLI executable and the Unity Editor bridge are two halves of one published package: the exe is installed at `CLI~/unity-puer-exec.exe` inside the same package tree as `Editor/*.cs`. Their versions are therefore equal by construction, and any observed difference means the halves were mixed. Today neither half can detect this, so a mixed installation runs silently and produces evidence that is attributed to the product rather than to the installation.

## What Changes

- Stamp the CLI's own version into the packaged executable at build time, sourced from `packages/com.txcombo.unity-puer-exec/package.json`, with an equivalent resolution path when the CLI runs from source.
- Add a `--version` entry that reports the CLI version without requiring a command.
- Include a top-level `cli_version` field in every machine-readable CLI response, so the acting build is recorded in any transcript without the caller having to ask.
- Expose a `bridge_version` field in the Unity control service `/health` response, sourced from the loaded package's own metadata.
- Add two version guards:
  - **Package-layout guard**: when the executable is invoked from its installed location inside a package tree, compare its stamped version against the adjacent `package.json`. This runs before any network activity.
  - **Bridge guard**: compare the CLI version against `bridge_version` from the control service health payload, on every command that contacts the service.
- Add a terminal status `version_mismatch` with exit code `24`. A command that detects either mismatch SHALL refuse to perform its work and return this status, naming both observed versions and which guard fired.
- Treat an absent `bridge_version` as a mismatch, not as a pass. A bridge that does not report a version predates this contract and cannot be assumed compatible.
- Match versions by exact string equality. The two halves ship from one package version, so anything other than equality is a mixed installation.
- **BREAKING**: mixed installations that previously ran and produced results now fail fast with exit `24`. This is the intended behavior change; the prior silent-success path is what produced the misattributed feedback.
- No bypass flag is introduced. The repository's own development path resolves both versions from the same package tree (`tools/prepare_validation_host.py` points the host manifest at `packages/com.txcombo.unity-puer-exec` via a `file:` dependency), so no legitimate workflow in this repository requires running mismatched halves.
- Add guidance matrix coverage for the new status so the refusal explains how to reconcile the installation.

## Capabilities

### New Capabilities

- `cli-version-compatibility`: version identity for both product halves, the two guard checks, exact-match policy, absent-version handling, and the refuse-to-run contract.

### Modified Capabilities

- `formal-cli-contract`: adds the `version_mismatch` status and exit code `24` to the formal machine contract, adds `--version`, and adds `cli_version` to the machine-readable response shape.
- `project-control-endpoint`: the health response identity requirement is extended to include `bridge_version`.
- `cli-binary-packaging`: the packaged executable requirement is extended so the binary reports the package version it was built from.
- `runtime-guidance`: the guidance matrix gains coverage for `version_mismatch`, keeping the "every documented non-success status has an entry" requirement satisfied.

## Impact

- `cli/python/unity_puer_exec_surface.py`: `--version` handling; guard invocation points.
- `cli/python/unity_puer_exec_runtime.py`: version resolution, guard evaluation, `version_mismatch` payload construction, `cli_version` injection into emitted responses.
- `cli/python/direct_exec_client.py`: `EXIT_VERSION_MISMATCH = 24`.
- `cli/python/help_surface.py`: `--version` documentation, status text, guidance matrix entry.
- New CLI module for version resolution (frozen-binary stamp vs source-tree `package.json`).
- `packages/com.txcombo.unity-puer-exec/Editor/UnityPuerExecProtocol.cs`: `bridge_version` in `BuildHealthResponseJson`.
- `packages/com.txcombo.unity-puer-exec/Editor/UnityPuerExecServer.cs`: version resolution for the bridge half.
- `.github/workflows/release.yml`: version-stamping step before the PyInstaller build.
- `tests/`: unit coverage for version resolution and both guards; real-host coverage for the bridge guard against a matched host.
- Consumers running mixed installations (for example a project vendoring an older package while invoking a newer executable) must align both halves before the CLI will run.
