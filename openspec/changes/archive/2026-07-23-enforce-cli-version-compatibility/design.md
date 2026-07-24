## Context

The 2026-07-23 external agent feedback round was investigated by interviewing the reporting agent and then verifying its claims against the repository. The verification established:

- The executable it ran, the copy vendored into the consuming game project, and the copy sitting untracked in this repository's `packages/com.txcombo.unity-puer-exec/CLI~/` are byte-identical (`sha256 3aba72be…`).
- That binary is the v0.6.0 release artifact (tag `2368edd`, 2026-06-17). `--full-text`, `--indexes`, `--response-file`, and `--stale-module-policy` are all absent from v0.6.0 source, matching the executable's observed behavior exactly.
- The release pipeline is sound: `v0.7.0` points at HEAD and its tree contains the flags, and `.github/workflows/release.yml` builds with PyInstaller from the tagged checkout. The published artifact is not stale.
- The agent's own version inference reported "package.json version: 0.7.0" because the untracked `CLI~/` binary sits beside the repository's `package.json`, which tracks HEAD.

Findings from the feedback round that remain true and are addressed by other changes, not this one: the empty `next_steps` on the `exec` / `wait-for-log-pattern` success statuses, the plain-text argparse error path, the undocumented JsEnv isolation boundary, and the `.start` vs `.end` offset ambiguity. Findings that were dissolved by the version discovery: the three "missing capability" claims. Findings that were withdrawn by the reporting agent after review: `--include-new-error-briefs`, and a PlayMode wait command (the transport was verified healthy across PlayMode transitions, with `session_marker` unchanged).

The gap this design addresses is narrower and more fundamental than any of those: the product has no version identity in either half, so a mixed installation cannot be detected by anyone — not the agent, not the maintainer reading the transcript, not the CLI itself.

The two halves ship as one artifact. `Editor/*.cs` and `CLI~/unity-puer-exec.exe` live in the same package tree and are published together by a single workflow run. Their versions are equal by construction; a difference is always a mixed installation.

## Goals / Non-Goals

**Goals:**

- Give each half a version it can report.
- Make the acting CLI build visible in every transcript without the caller asking for it.
- Detect a mixed installation and refuse to act on it, before the command performs work.
- Make an unversioned counterpart (a build predating this contract) a detected condition, not a silent pass.
- Keep the check free of maintained compatibility tables.

**Non-Goals:**

- Version negotiation, capability handshakes, or graceful degradation across versions. The halves ship together; there is no independent-upgrade story to support.
- Fixing the untracked, un-gitignored `CLI~/` directory in this repository's working tree, or documenting a rebuild step in `validation-host-integration/how-to-run.md`. Those are maintainer-workflow hygiene and are tracked separately as follow-up candidates.
- Changing how consumers install or vendor the package.
- Retrofitting version reporting into already-released versions.

## Decisions

### D1: The CLI version is stamped at build time into a generated module

The release workflow writes `cli/python/_build_version.py` containing the version read from `packages/com.txcombo.unity-puer-exec/package.json`, immediately before the PyInstaller invocation. At runtime the CLI imports it. When running from source (the module is absent), the CLI resolves the version by reading that same `package.json` relative to the source tree.

*Alternatives considered.* Bundling `package.json` via PyInstaller `--add-data` was rejected: onefile builds extract data to a temporary directory, so path resolution becomes environment-dependent for no benefit. A Windows PE version resource via `--version-file` was rejected: it is platform-specific metadata that Python cannot read back portably without an added dependency.

*Consequence that matters.* If a frozen binary has no stamp, that is a build defect, and the binary must not be allowed to run unguarded — an unstamped binary is exactly the shape of the artifact that caused this incident. A frozen build with a missing stamp is therefore reported as `cli_version_unknown` and refuses, rather than falling back to a source-tree lookup that would silently succeed against an unrelated checkout.

### D2: The bridge version comes from Unity's package metadata

The Editor half resolves its version through `UnityEditor.PackageManager.PackageInfo.FindForAssembly(...)` on its own assembly and includes the result as `bridge_version` in the `/health` payload built by `UnityPuerExecProtocol.BuildHealthResponseJson`.

*Alternative considered.* Reading `package.json` from a path derived from the script location was rejected as fragile across embedded, UPM-cached, and local `file:` installs; `PackageInfo` is the supported API and handles all three.

*Consequence that matters.* If the Editor scripts are not installed as a package — for example copied into `Assets/` — `FindForAssembly` returns null and no `bridge_version` is emitted. Per D5 that is treated as a mismatch. This is the correct outcome: an installation that cannot state its version cannot be verified, and the product's packaging contract already requires the package tree.

### D3: Versions match by exact string equality

No semver range, no minor-level tolerance, no compatibility matrix.

*Rationale.* The halves are published from one `package.json` by one workflow run. Any policy looser than equality would be describing a scenario that the release process does not produce, while requiring someone to maintain a compatibility table that would go stale. This repository's 0.x minor releases also carry contract changes (statuses, exit codes, flags), so minor-level tolerance would admit exactly the mismatches that matter.

### D4: No bypass flag

`--allow-version-mismatch` was considered and rejected.

*Rationale.* Agents retry failed commands with permissive flags; a documented bypass converts a hard guarantee into a speed bump, and the failure mode this change exists to prevent is precisely an agent proceeding on a mismatched pair. The objection to omitting a bypass is that it could block a legitimate workflow, but this repository has none: `tools/prepare_validation_host.py` points the validation host's `manifest.json` at `packages/com.txcombo.unity-puer-exec` through a `file:` dependency, so a source-run CLI and the host's bridge resolve their versions from the same tree and match by construction.

*Mitigation for the caller who is genuinely stuck.* The refusal is mechanical to resolve, so the payload must make it so: it names both versions, the source of each (executable path and control endpoint), and the reconciliation action, with guidance-matrix `next_steps` attached.

### D5: An absent counterpart version is a mismatch, not a pass

A bridge that reports no `bridge_version` predates this contract. Treating that as "unknown, therefore allow" would make the guard inert in the one case it is most needed — an old half paired with a new one. It is reported as a mismatch with `observed_version: null` and a guard value distinguishing it from a genuine version difference.

### D6: Two guards, ordered cheapest first

**Package-layout guard.** When the executable resolves to an installed package layout, compare the stamped version against the adjacent `package.json`. Local, no network, runs before any session work. This is the guard that catches the exact configuration behind this incident. It is skipped — not failed — when the executable is not inside a package layout, because a standalone copy is a legitimate deployment.

**Bridge guard.** Compare the CLI version against `bridge_version` from the health payload, on every command that contacts the control service, in both `--project-path` and `--base-url` mode, before the command performs its work.

### D7: `cli_version` is a top-level field on every response

Including non-success payloads. It costs roughly twenty-five bytes against responses that already carry `log_range` and `brief_sequence`, and it is the mechanism that makes a transcript self-diagnosing after the fact — the property whose absence made this incident invisible to both the reporting agent and the maintainer. It is added to the response-file routing fields so the compact reference emitted under `--response-file` carries it too.

### D8: `--version` is intercepted before argparse

The top-level parser declares `subparsers(required=True)`, so a bare `--version` would fail as a missing-command error. It is handled with the same pre-parse interception already used for `--help`, `--help-args`, and `--help-status`.

## Risks / Trade-offs

- **A new CLI paired with a pre-guard bridge always refuses.** → Intended, and the resolution is one action because the halves ship together. The refusal names the package path so the caller knows what to upgrade. Accepted cost of making the guard meaningful.
- **An old CLI paired with a new bridge remains unguarded.** → Unavoidable; a released binary cannot be taught to read a field it does not know about. The guard becomes fully effective only once both halves are at or above the release introducing it. Documented as a known limitation rather than worked around.
- **A build that omits the stamping step refuses every command.** → Intended per D1, but it converts a workflow slip into total breakage. Mitigation: the release workflow asserts the stamp is present in the built artifact before assembling the package tree, so the failure surfaces in CI rather than at a user.
- **`PackageInfo.FindForAssembly` returning null blocks non-package installs.** → Correct by D2's reasoning, but it is a behavior change for anyone who copied the Editor scripts outside a package. The refusal text must name this case explicitly so it is self-diagnosing.
- **Exact matching makes local experimentation stricter.** → The repository's own paths match by construction (D4). Contributors who hand-assemble a mixed tree will be told exactly which two versions disagree.
- **Adding a required field to `/health` touches the endpoint identity contract.** → Additive only; existing consumers ignore unknown fields, and the CLI's handling of the field's absence is specified rather than incidental.
