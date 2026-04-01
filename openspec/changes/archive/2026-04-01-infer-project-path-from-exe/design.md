## Context

The CLI currently resolves the Unity project path through a three-step chain: explicit `--project-path` argument, `UNITY_PROJECT_PATH` environment variable (loaded from `.env`), then cwd fallback. AI Agents—the primary callers—always discover the exe by absolute path before invoking it, so the project root is already implicit in the call. The exe is built with PyInstaller `--onefile` and distributed inside the UPM package at `CLI~/unity-puer-exec.exe`.

PyInstaller `--onefile` extracts to a temp directory at runtime, so `sys.executable` and `__file__` point to the temp path. However, `sys.argv[0]` preserves the caller-supplied invocation string. Combined with `Path.resolve()` (which uses cwd for relative paths), this recovers the exe's real install location.

## Goals / Non-Goals

**Goals:**
- Make `--project-path` optional for the most common scenario: Agent invokes the exe by absolute path from within a Unity project's package tree.
- Keep all existing explicit-path and env-var workflows working unchanged.
- Fail silently when inference is not possible, falling back to existing resolution steps.

**Non-Goals:**
- Switching from `--onefile` to `--onedir` packaging.
- Handling PATH-based invocations where `sys.argv[0]` contains no directory information.
- Making `--base-url` mode aware of project inference (it has no project-path concept).

## Decisions

### 1. Use `sys.argv[0]` resolved against cwd, not `sys.executable`

**Choice**: `Path(sys.argv[0]).resolve()` to recover the exe's original filesystem location.

**Why**: `sys.executable` in `--onefile` mode points to the temp extraction directory. `sys.argv[0]` retains whatever the OS received from the caller—typically an absolute path when an Agent invokes the exe. `Path.resolve()` handles the relative-path case by joining with cwd.

**Alternative considered**: Add a `--exe-origin` parameter for the caller to pass the exe path explicitly. Rejected because it shifts work to the caller without benefit—the caller already knows the project path if it knows the exe path, so `--project-path` already serves that role.

### 2. Walk up parents looking for `Packages/manifest.json` with package verification

**Choice**: From the resolved exe path, iterate `parent` upward. At each level, check if `Packages/manifest.json` exists and contains `"com.txcombo.unity-puer-exec"` as a key in `dependencies`.

**Why**: A fixed parent-count (e.g. 5 levels up) breaks across different install modes (PackageCache, embedded, local file reference). Walking up with manifest verification is robust to all UPM install layouts:
- `Library/PackageCache/com.txcombo.unity-puer-exec@ver/CLI~/exe` → 5 levels
- `Packages/com.txcombo.unity-puer-exec/CLI~/exe` → 3 levels
- Any future nesting depth

The manifest content check (`"com.txcombo.unity-puer-exec"` in dependencies) prevents false matches against unrelated Unity projects higher in the directory tree.

**Alternative considered**: Only check for `Packages/manifest.json` existence without reading content. Rejected because nested Unity projects could cause false matches.

### 3. Insert inference after env var, before cwd fallback

**Choice**: Resolution order becomes:
1. `--project-path` (explicit argument)
2. `UNITY_PROJECT_PATH` (environment variable / `.env`)
3. Exe origin inference (new)
4. `cwd` fallback

**Why**: Both `--project-path` and `UNITY_PROJECT_PATH` represent explicit user intent and must override automatic inference. The cwd fallback is the weakest heuristic and stays last. During development, `.env` typically points to a different project than where the exe source lives, so env-var priority over inference preserves the development workflow.

### 4. Pass `argv0` through the resolution chain

**Choice**: Add an `argv0` parameter to `resolve_project_path()`. The CLI entry point passes `sys.argv[0]`. Tests can inject synthetic values.

**Why**: Keeps the inference logic testable without monkey-patching `sys.argv`. The parameter is `None` by default; when `None`, inference is skipped (consistent with library callers that don't run as a packaged exe).

## Risks / Trade-offs

**[Risk] `sys.argv[0]` doesn't contain path info** → When invoked via PATH lookup, `sys.argv[0]` may be just `unity-puer-exec` with no directory component. `Path("unity-puer-exec").resolve()` resolves against cwd, which is unlikely to be the exe's real location. **Mitigation**: The walk-up search will simply not find `Packages/manifest.json` and return `None`, falling through to cwd fallback. No incorrect inference occurs.

**[Risk] Symlinked exe path** → If the exe is symlinked, `Path.resolve()` follows symlinks and may point to a location outside the Unity project. **Mitigation**: This is an unusual setup. The manifest check prevents false positives. If inference fails, the caller can still use `--project-path`.

**[Risk] `Packages/manifest.json` read adds I/O on every CLI invocation** → **Mitigation**: The file is typically <2KB and read at most once during the upward walk. The cost is negligible compared to the HTTP round-trip that follows.
