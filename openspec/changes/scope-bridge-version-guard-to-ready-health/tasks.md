## 1. Unity compiling health reports known version

- [x] 1.1 Include `bridge_version` in compiling (and bound `not_available`) health JSON when `BuildHealthResponseJson` already has a non-empty version, keeping session_marker; verify with a C# protocol unit assertion or an equivalent Python test that the compiled JSON string for compiling contains `bridge_version`.
- [x] 1.2 Keep omitting `bridge_version` when the resolved package version is empty; verify the not-package-installed compiling/ready path still omits the field.

## 2. CLI missing-version guard is ready-only

- [x] 2.1 Make `check_bridge` / owned-endpoint extra probe treat omitted `bridge_version` as mismatch only when health `status` is `ready`; verify `test_cli_version.py` covers compiling-without-version is not a mismatch.
- [x] 2.2 Keep comparing `bridge_version` when a compiling payload carries one; verify compiling + disagreeing version still yields `guard: bridge`.
- [x] 2.3 Keep ready-without-version as `bridge_version_unknown`; verify the existing ready-omitted-version test still fails the command with exit 24.

## 3. Command entry points use the same rule

- [x] 3.1 Apply the ready-only missing-version rule to `_base_url_bridge_guard` so `--base-url` commands do not refuse on compiling stubs; verify a mocked compiling `/health` plus `exec --base-url` / `wait-for-compile --base-url` does not return `version_mismatch`.
- [x] 3.2 Apply the same rule to `ensure_session_ready` extra probe so project-scoped `exec --refresh-before-exec` does not refuse after refresh starts compile; verify a mocked post-refresh compiling payload does not raise `UnityVersionMismatchError` for missing version.

## 4. Closeout

- [x] 4.1 Run the repository unit suite (`python -m pytest tests/` per `openspec/specs/validation-host-integration/how-to-run.md`) and record pass/fail on the new and existing version-guard tests.
- [x] 4.2 Confirm each modified `cli-version-compatibility` and `project-control-endpoint` scenario has a test or an explicit host-validation skip reason.
- [x] 4.3 Produce the apply closeout finding summary and recommend the commit / `openspec archive` / final commit sequence.
