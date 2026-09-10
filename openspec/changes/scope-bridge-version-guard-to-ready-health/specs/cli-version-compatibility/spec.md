## MODIFIED Requirements

### Requirement: The Unity bridge reports its package version

The Unity control service SHALL include a `bridge_version` field in its `/health` response, resolved from the Unity package metadata for the assembly that provides the service. When that version is known, the field SHALL be present for both ready and non-ready health statuses that the bound service emits (`ready`, `compiling`, and `not_available`).

#### Scenario: Health response on a package-installed bridge

- **WHEN** a caller probes `/health` on a ready service whose Editor assembly belongs to an installed package
- **THEN** the response includes `bridge_version` set to that package's version

#### Scenario: Compiling health on a package-installed bridge

- **WHEN** a caller probes `/health` while the Editor is compiling or reloading and the Editor assembly belongs to an installed package
- **THEN** the response includes `status = "compiling"`
- **AND** the response includes `bridge_version` set to that package's version

#### Scenario: Bridge assembly does not belong to a package

- **WHEN** the Editor assembly providing the service does not belong to an installed Unity package
- **THEN** the health response SHALL omit `bridge_version` or report it as null rather than reporting a guessed value

### Requirement: The CLI verifies its version against the control service

Every command that contacts the Unity control service SHALL compare the CLI version against the `bridge_version` reported by that service before performing the command's work, in both `--project-path` and `--base-url` mode. A reachable health payload whose `status` is not `ready` and that omits `bridge_version` SHALL NOT, by itself, satisfy this comparison as a mismatch; the command SHALL treat that payload as not yet version-observable and continue its normal non-ready handling (wait, compiling continuation, or the command's own not-ready status).

#### Scenario: Bridge version disagrees with CLI version

- **WHEN** a command obtains a health response whose `bridge_version` differs from the CLI version
- **THEN** the command SHALL return `version_mismatch` with a guard value of `bridge`
- **AND** the response SHALL name both versions and the control endpoint
- **AND** the command SHALL NOT execute scripts, start observation, or otherwise perform its work

#### Scenario: Guard applies in direct base-url mode

- **WHEN** a command targets a service through `--base-url` and the reported `bridge_version` differs from the CLI version
- **THEN** the command SHALL return `version_mismatch` on the same terms as project-scoped mode

#### Scenario: Compiling health without a version is not a mixed installation

- **WHEN** a command obtains a health response with `status = "compiling"` (or `not_available`) that omits `bridge_version` or reports it as null
- **THEN** the command SHALL NOT return `version_mismatch` solely because the version is absent
- **AND** the command SHALL continue the compile, recovery, or not-ready path that status already defines

#### Scenario: Compiling health with a disagreeing version is still a mismatch

- **WHEN** a command obtains a health response with `status = "compiling"` whose `bridge_version` differs from the CLI version
- **THEN** the command SHALL return `version_mismatch` with a guard value of `bridge`
- **AND** the command SHALL NOT perform its work

### Requirement: An unavailable counterpart version is a mismatch

When a **ready** counterpart does not report a version, the CLI SHALL treat the condition as a mismatch rather than as an unverified pass, because a ready counterpart that cannot state its version predates or falls outside this contract. This requirement SHALL NOT apply to a non-ready health payload that omits `bridge_version`.

#### Scenario: Bridge reports no version

- **WHEN** a ready health response omits `bridge_version` or reports it as null
- **THEN** the command SHALL return `version_mismatch`
- **AND** the reported counterpart version SHALL be null
- **AND** the guard value SHALL distinguish this case from a genuine version difference

#### Scenario: Non-ready health without a version is not this mismatch

- **WHEN** a health response is not ready and omits `bridge_version` or reports it as null
- **THEN** the command SHALL NOT return `version_mismatch` under this requirement
