## Why

AI Agents invoking the CLI almost always discover `unity-puer-exec.exe` by its absolute path first, then build the command line. The exe's install location already implies the Unity project root. Requiring callers to also supply `--project-path` or configure `UNITY_PROJECT_PATH` is unnecessary friction for the most common usage scenario. Letting the CLI infer the project path from its own install location makes `--project-path` optional in typical use.

## What Changes

- Add an "exe origin inference" step to the project-path resolution chain: resolve the exe's real install location from `sys.argv[0]`, walk up parent directories looking for `Packages/manifest.json`, and verify it contains `com.txcombo.unity-puer-exec` to confirm the Unity project root.
- Resolution priority becomes: `--project-path` > `UNITY_PROJECT_PATH` env var > exe origin inference > cwd fallback.
- When inference fails (e.g. exe not inside a Unity project, manifest doesn't reference this package), silently fall back to subsequent steps. No breaking change.

## Capabilities

### New Capabilities
- `exe-origin-project-inference`: CLI infers the Unity project root from its own install path by walking up to find `Packages/manifest.json` and verifying the package reference.

### Modified Capabilities
- `formal-cli-contract`: The "deterministic resolution order" for project-path gains the exe origin inference step. `--project-path` becomes effectively optional for selector-driven commands when the exe is installed inside a Unity project.

## Impact

- `cli/python/unity_session_env.py`: `resolve_project_path` gains inference logic.
- `cli/python/unity_puer_exec_surface.py`: may need `--project-path` help text update.
- `openspec/specs/formal-cli-contract/spec.md`: update selector-driven addressing and resolution order requirements.
- Tests: unit tests for the inference logic.
- Relies on PyInstaller `--onefile` preserving the caller-supplied path in `sys.argv[0]`. When the exe is invoked via PATH lookup with no path info, inference is unavailable and existing behavior applies.
