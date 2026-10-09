## 1. Preflight helper

- [ ] 1.1 Add a `tools/` helper that resolves the validation host and Unity executable through the existing paths (`prepare_validation_host`, `unity_session._resolve_unity_exe_path`) and the `.env` launch-argument input, then runs `Unity -batchMode -quit -nographics -projectPath <host> -logFile <private log>`. Verify: the helper runs without an interactive Editor and returns the batch exit code and log path.
- [ ] 1.2 Parse `error CS` diagnostics from the batch log on a non-zero exit and return them as structured failure detail. Verify: a unit test feeds a synthetic log with two `error CS` lines and asserts both are returned; a non-zero exit with no `error CS` reports the exit code and log path instead.
- [ ] 1.3 Skip cleanly when the host project, manifest, or Unity executable is unavailable, using the same resolution the suite already uses. Verify: a unit test asserts a skip result rather than an exception when a prerequisite is missing.

## 2. Wire the preflight into the real-host suite

- [ ] 2.1 Invoke the preflight once per suite invocation, before the first interactive launch, and cache the result for the process. Verify: a run with several classes invokes the batch preflight exactly once.
- [ ] 2.2 On a compile failure, fail the real-host run with the parsed diagnostics before any interactive Editor is launched. Verify: an injected failing preflight result fails the run without calling the interactive launcher.
- [ ] 2.3 Preserve the opt-in gate and the shared-host reuse model; do not add a per-class preflight. Verify: the default (non-gated) unit suite still does not launch Unity.

## 3. Validation

- [ ] 3.1 Reproduce the original failure class: introduce a deliberate `error CS` in a scratch copy of a package file (or a mocked batch log), confirm the preflight fails with the parsed diagnostic, then revert. Verify: the failure names the file and error code, not the Safe Mode dialog.
- [ ] 3.2 Run the real-host suite with a compilable package and confirm the preflight passes and the interactive run proceeds. Verify: green, and the batch log shows no `error CS`.
- [ ] 3.3 Add unit tests for the diagnostic parser, the skip path, and the once-per-invocation guard. Verify: `python -m unittest` (default module list plus the new test module) passes.
- [ ] 3.4 Run `openspec validate preflight-compile-check-before-editor-launch`. Verify: green.
