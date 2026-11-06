# Spec Delta

## ADDED Requirements

### Requirement: Real-host validation covers ES module import resolution and explicit JsEnv reset

The real-host suite SHALL cover `exec --import-base-url` resolving a relative ES module import
against a live Editor, and SHALL cover `exec --reset-jsenv-before-exec` observably clearing
JavaScript environment state. The reset case SHALL distinguish the explicit flag from the
default same-invocation recovery of a changed module, so it cannot pass without the flag being
exercised. Both cases SHALL run against the shared host device rather than adding an Editor
launch.

#### Scenario: A relative import resolves through a filesystem base URL

- **WHEN** a real-host case runs `exec --code` whose entry module imports a sibling module by
  relative specifier
- **AND** `--import-base-url` names a filesystem directory containing that module
- **THEN** the request reaches a terminal `completed` status
- **AND** the imported module's exported value appears in the response `result`, proving
  resolution happened rather than merely that no error was raised

#### Scenario: An explicit reset is distinguishable from default staleness recovery

- **WHEN** a real-host case runs `exec --reset-jsenv-before-exec` after an earlier exec stored
  state in `ctx.globals`
- **AND** the module source is unchanged between the two requests
- **THEN** the stored state is gone in the second request
- **AND** the case would fail if the explicit reset silently stopped happening, which a
  changed-module-only assertion would not detect because default staleness recovery already
  reloads a changed module

#### Scenario: The cases do not add an Editor launch

- **WHEN** the real-host suite runs with these cases present
- **THEN** they execute against the shared host device
- **AND** the suite's Editor launch count is unchanged from before the cases were added

#### Scenario: The cases leave no residue in the host project

- **WHEN** the import and reset cases finish
- **THEN** any module fixture they wrote is removed by the suite's existing per-case cleanup
- **AND** a host project under version control reports no new or modified tracked file from the
  run

#### Scenario: Coverage holds on every supported PuerTS major

- **WHEN** the real-host suite runs against a host whose `com.tencent.puerts.core` is a
  supported major
- **THEN** the import and reset cases pass on that host
- **AND** a failure on one supported major and not another is reported as a version-specific
  regression rather than as a host problem
