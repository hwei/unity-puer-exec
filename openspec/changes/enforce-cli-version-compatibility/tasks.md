## 1. CLI version resolution

- [ ] 1.1 Add a CLI version-resolution module that returns the stamped version when frozen and the source-tree `packages/com.txcombo.unity-puer-exec/package.json` version otherwise, and reports an explicit unknown state for a frozen build with no stamp.
- [ ] 1.2 Add unit tests covering all three resolution paths, including that the frozen-without-stamp path does not fall back to reading a `package.json` from the filesystem.
- [ ] 1.3 Add `EXIT_VERSION_MISMATCH = 24` to `direct_exec_client.py` and include it in the expected-exit-code set.

## 2. Version surfacing

- [ ] 2.1 Intercept `--version` before argparse in `unity_puer_exec_surface.py`, alongside the existing `--help` / `--help-args` / `--help-status` handling, so a bare `--version` does not fail on the required subcommand.
- [ ] 2.2 Inject a top-level `cli_version` into every emitted payload in `unity_puer_exec_runtime.py`, covering success, expected-failure, and unexpected-failure payload builders.
- [ ] 2.3 Add `cli_version` to `_RESPONSE_FILE_ROUTING_FIELDS` so the compact `--response-file` reference retains it.
- [ ] 2.4 Add unit tests asserting `cli_version` is present on all three payload families and on a `--response-file` compact reference.
- [ ] 2.5 Exempt `--version` and the help entries from both guards, and add tests confirming they still answer on an installation that fails a guard, including a frozen build with no stamp.
- [ ] 2.6 Survey the existing suite for tests that assert whole-payload equality before adding `cli_version`, and contain the ripple with a shared presence assertion plus a normalizer that strips the field for existing golden comparisons, rather than pasting the field into every expected payload.

## 3. Bridge version reporting

- [ ] 3.1 Resolve the package version in the Editor half via `UnityEditor.PackageManager.PackageInfo.FindForAssembly(...)`, returning null when the assembly does not belong to an installed package.
- [ ] 3.2 Add `bridge_version` to `UnityPuerExecProtocol.BuildHealthResponseJson` and thread the resolved value from `UnityPuerExecServer` health handling.
- [ ] 3.3 Verify against the validation host that `/health` reports a `bridge_version` equal to the repository package version.

## 4. Package-layout guard

- [ ] 4.1 Detect whether the running executable resolves to an installed package layout, reusing the existing exe-origin resolution path.
- [ ] 4.2 Compare the resolved CLI version against the adjacent `package.json` version and produce a `version_mismatch` result with guard `package_layout` on disagreement.
- [ ] 4.3 Skip the guard without failing when the executable is not inside a package layout.
- [ ] 4.4 Add unit tests for match, mismatch, and not-in-package-layout, asserting the guard performs no network activity.
- [ ] 4.5 Reproduce the originating incident layout specifically: a `CLI~/` executable stamped `0.6.0` beside a `package.json` declaring `0.7.0`, and assert the guard fires. This is the guard that catches that incident; the bridge guard does not, because the runtime pair in that incident was internally consistent.

## 5. Bridge guard

- [ ] 5.1 Compare the CLI version against health `bridge_version` at the point the health payload first becomes available, for both `--project-path` and `--base-url` selectors.
- [ ] 5.2 Produce `version_mismatch` with guard `bridge` on disagreement, and with a distinct guard value when `bridge_version` is absent or null.
- [ ] 5.3 Fire the guard on the first health payload that carries `bridge_version`, including pre-`ready` payloads, so no work happens between the field becoming observable and the refusal. Launching Unity during project-scoped startup does not count as performing work; executing a script, accepting an exec request, or starting observation does.
- [ ] 5.4 Add unit tests covering match, differing version, absent `bridge_version`, and base-url mode.

## 6. Response shape and guidance

- [ ] 6.1 Build the `version_mismatch` payload carrying guard identity, CLI version, observed counterpart version (nullable), and observed location (package path or control endpoint).
- [ ] 6.2 Add guidance-matrix entries for `version_mismatch` with per-guard `situation` text and `next_steps` limited to verification actions, referencing no bypass and not re-running the failed command.
- [ ] 6.3 Ensure `--suppress-guidance` removes `next_steps` and `situation` but retains the structured version detail.
- [ ] 6.4 Add `version_mismatch` and exit code `24` to `--help-status` for every command that contacts the control service, and document `--version` in top-level help global options.
- [ ] 6.5 Add unit tests for guidance content, suppression behavior, and help rendering.

## 7. Build stamping

- [ ] 7.1 Add a release-workflow step that writes the stamped version module from `packages/com.txcombo.unity-puer-exec/package.json` before the PyInstaller invocation.
- [ ] 7.2 Add a post-build assertion that the built executable reports a stamped version equal to the package version, failing the workflow before the UPM package tree is assembled.
- [ ] 7.3 Confirm a locally built executable reports the expected version via `--version`.

## 8. Validation and closeout

- [ ] 8.1 Run the repository unit suite and confirm no regressions.
- [ ] 8.2 Run the real-host suite against the validation host and confirm the bridge guard passes on a matched installation.
- [ ] 8.3 Verify the mismatch path against a real host by pointing a deliberately mismatched CLI version at the host and confirming `version_mismatch` with exit `24` and no work performed.
- [ ] 8.4 Run `openspec validate enforce-cli-version-compatibility` and confirm the change remains valid.
- [ ] 8.5 Record the apply closeout finding summary, stating either `No new follow-up work identified` or `New follow-up candidates identified`.
