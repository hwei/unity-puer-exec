## 1. Core inference logic

- [ ] 1.1 Add `_infer_project_from_exe(argv0)` to `cli/python/unity_session_env.py`: resolve `argv0` via `Path.resolve()`, walk up parents, find `Packages/manifest.json`, verify `com.txcombo.unity-puer-exec` in dependencies, return project root or `None`
- [ ] 1.2 Add `argv0` parameter to `resolve_project_path()` and insert the inference step between env-var lookup and cwd fallback
- [ ] 1.3 Wire `sys.argv[0]` through the call chain: `unity_session.py` → `unity_session_env.resolve_project_path(argv0=...)`; the runtime entry point passes `sys.argv[0]` when invoking resolution

## 2. Unit tests

- [ ] 2.1 Test inference with a synthetic directory tree mimicking PackageCache layout (manifest present, package listed) → returns project root
- [ ] 2.2 Test inference with embedded-package layout (`Packages/com.txcombo.../CLI~/exe`) → returns project root
- [ ] 2.3 Test inference when manifest exists but does not reference `com.txcombo.unity-puer-exec` → returns `None`
- [ ] 2.4 Test inference when no manifest exists in any ancestor → returns `None`
- [ ] 2.5 Test resolution priority: `--project-path` > env var > inference > cwd

## 3. CLI surface and spec updates

- [ ] 3.1 Update `--project-path` help text in `unity_puer_exec_surface.py` to note it is optional when the exe is installed inside a Unity project
- [ ] 3.2 Update `openspec/specs/formal-cli-contract/spec.md` with the modified selector-driven addressing requirement
- [ ] 3.3 Create durable spec `openspec/specs/exe-origin-project-inference/spec.md` from the change spec
