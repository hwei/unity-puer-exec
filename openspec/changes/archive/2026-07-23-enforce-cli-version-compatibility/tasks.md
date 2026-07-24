## 1. CLI version resolution

- [x] 1.1 Add a CLI version-resolution module that returns the stamped version when frozen and the source-tree `packages/com.txcombo.unity-puer-exec/package.json` version otherwise, and reports an explicit unknown state for a frozen build with no stamp.
- [x] 1.2 Add unit tests covering all three resolution paths, including that the frozen-without-stamp path does not fall back to reading a `package.json` from the filesystem.
- [x] 1.3 Add `EXIT_VERSION_MISMATCH = 24` to `direct_exec_client.py` and include it in the expected-exit-code set.

## 2. Version surfacing

- [x] 2.1 Intercept `--version` before argparse in `unity_puer_exec_surface.py`, alongside the existing `--help` / `--help-args` / `--help-status` handling, so a bare `--version` does not fail on the required subcommand.
- [x] 2.2 Inject a top-level `cli_version` into every emitted payload in `unity_puer_exec_runtime.py`, covering success, expected-failure, and unexpected-failure payload builders.
- [x] 2.3 Add `cli_version` to `_RESPONSE_FILE_ROUTING_FIELDS` so the compact `--response-file` reference retains it.
- [x] 2.4 Add unit tests asserting `cli_version` is present on all three payload families and on a `--response-file` compact reference.
- [x] 2.5 Exempt `--version` and the help entries from both guards, and add tests confirming they still answer on an installation that fails a guard, including a frozen build with no stamp.
- [x] 2.6 Survey the existing suite for tests that assert whole-payload equality before adding `cli_version`, and contain the ripple with a shared presence assertion plus a normalizer that strips the field for existing golden comparisons, rather than pasting the field into every expected payload.

## 3. Bridge version reporting

- [x] 3.1 Resolve the package version in the Editor half via `UnityEditor.PackageManager.PackageInfo.FindForAssembly(...)`, returning null when the assembly does not belong to an installed package.
- [x] 3.2 Add `bridge_version` to `UnityPuerExecProtocol.BuildHealthResponseJson` and thread the resolved value from `UnityPuerExecServer` health handling.
- [x] 3.3 Verify against the validation host that `/health` reports a `bridge_version` equal to the repository package version.

## 4. Package-layout guard

- [x] 4.1 Detect whether the running executable resolves to an installed package layout, reusing the existing exe-origin resolution path.
- [x] 4.2 Compare the resolved CLI version against the adjacent `package.json` version and produce a `version_mismatch` result with guard `package_layout` on disagreement.
- [x] 4.3 Skip the guard without failing when the executable is not inside a package layout.
- [x] 4.4 Add unit tests for match, mismatch, and not-in-package-layout, asserting the guard performs no network activity.
- [x] 4.5 Reproduce the originating incident layout specifically: a `CLI~/` executable stamped `0.6.0` beside a `package.json` declaring `0.7.0`, and assert the guard fires. This is the guard that catches that incident; the bridge guard does not, because the runtime pair in that incident was internally consistent.

## 5. Bridge guard

- [x] 5.1 Compare the CLI version against health `bridge_version` at the point the health payload first becomes available, for both `--project-path` and `--base-url` selectors.
- [x] 5.2 Produce `version_mismatch` with guard `bridge` on disagreement, and with a distinct guard value when `bridge_version` is absent or null.
- [x] 5.3 Fire the guard on the first health payload that carries `bridge_version`, including pre-`ready` payloads, so no work happens between the field becoming observable and the refusal. Launching Unity during project-scoped startup does not count as performing work; executing a script, accepting an exec request, or starting observation does.
- [x] 5.4 Add unit tests covering match, differing version, absent `bridge_version`, and base-url mode.

## 6. Response shape and guidance

- [x] 6.1 Build the `version_mismatch` payload carrying guard identity, CLI version, observed counterpart version (nullable), and observed location (package path or control endpoint).
- [x] 6.2 Add guidance-matrix entries for `version_mismatch` with per-guard `situation` text and `next_steps` limited to verification actions, referencing no bypass and not re-running the failed command.
- [x] 6.3 Ensure `--suppress-guidance` removes `next_steps` and `situation` but retains the structured version detail.
- [x] 6.4 Add `version_mismatch` and exit code `24` to `--help-status` for every command that contacts the control service, and document `--version` in top-level help global options.
- [x] 6.5 Add unit tests for guidance content, suppression behavior, and help rendering.

## 7. Build stamping

- [x] 7.1 Add a release-workflow step that writes the stamped version module from `packages/com.txcombo.unity-puer-exec/package.json` before the PyInstaller invocation.
- [x] 7.2 Add a post-build assertion that the built executable reports a stamped version equal to the package version, failing the workflow before the UPM package tree is assembled.
- [x] 7.3 Confirm a locally built executable reports the expected version via `--version`.

## 8. Validation and closeout

- [x] 8.1 Run the repository unit suite and confirm no regressions.
- [x] 8.2 Run the real-host suite against the validation host and confirm the bridge guard passes on a matched installation.
- [x] 8.3 Verify the mismatch path against a real host by pointing a deliberately mismatched CLI version at the host and confirming `version_mismatch` with exit `24` and no work performed.
- [x] 8.4 Run `openspec validate enforce-cli-version-compatibility` and confirm the change remains valid.
- [x] 8.5 Record the apply closeout finding summary, stating either `No new follow-up work identified` or `New follow-up candidates identified`.

## Apply closeout

**New follow-up candidates identified.**

- `product-improvement`: `get-compile-errors` / `get-compile-warnings` are not members of
  `help_surface.COMMANDS`, so they receive no `version_mismatch` guidance-matrix entry and no
  `--help-status` line, even though both local guards can make them return exit `24`. The
  durable `runtime-guidance` spec says "all ten commands", so this is conformant today, but the
  two commands can now emit a status their help does not document.
- `workflow-improvement`: the validation host carried an embedded v0.6.0 copy of the package at
  `Project/Packages/com.txcombo.unity-puer-exec`, which Unity resolves as an embedded package by
  its `package.json` `name` -- renaming the directory does **not** clear the shadow, it must be
  moved out of `Packages/`. `tools/prepare_validation_host.py` reports the condition but offers
  no way to resolve it, and `validation-host-integration/how-to-run.md` does not state the
  rename-is-not-enough fact.
- `validation-gap`: `test_exec_checkpoint_observation_chain_against_real_host` fails
  reproducibly against this validation host, and
  `test_exec_timeout_recovery_avoids_disconnect_noise_against_real_host` fails intermittently.
  Both were confirmed **pre-existing** by re-running the first against a stashed pre-change tree,
  where it fails identically. Neither involves `version_mismatch`.

### Real-host evidence recorded during this apply

- `/health` on the matched host reports `bridge_version` `0.7.0`, equal to the repository
  package version (task 3.3).
- Real-host suite: 18 tests, 16 pass, 3 skip, 2 pre-existing failures. The bridge guard fired
  no false refusal anywhere on a matched installation (task 8.2).
- A deliberately mismatched CLI (`0.6.0`) against the `0.7.0` bridge returned
  `version_mismatch` / guard `bridge` / exit `24`, and a follow-up probe confirmed the refused
  script's side effect never reached the JsEnv (task 8.3).
- A locally built PyInstaller executable reported `unity-puer-exec 0.7.0`, and the same binary
  placed in a `CLI~/` directory beside a disagreeing `package.json` refused with exit `24`
  before any network activity (task 7.3).

### Second defect found and fixed during closeout

The stamping step's PowerShell here-string was written with its body and `"@` terminator at
column 0, which silently ends the enclosing YAML block scalar -- so `release.yml` did not parse
and the release workflow would have failed on the next tag push. The substring-based workflow
test accepted it. Rewritten as an indentation-safe `Set-Content -Value @(...)` array, verified
by parsing the workflow and executing the rendered command, and guarded by
`test_release_workflow_is_parseable_yaml_with_a_runnable_stamp_step`.

### Defect found and fixed during real-host validation

The first real-host exec succeeded against an unversioned v0.6.0 bridge. The launch and
recovery paths lock onto the project's port through pre-`ready` payloads, which are checked with
`require_version=False`, so an unverifiable bridge slipped past and a script executed on it --
violating the refuse-before-work contract. `ensure_session_ready` now performs a final
version-required check once the endpoint is ready, covered by
`test_launch_path_still_gates_before_the_command_executes_anything`.
