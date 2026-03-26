## MODIFIED Requirements

### Requirement: The CLI has one primary entry and flat command tree

The formal CLI SHALL use `unity-puer-exec` as its single primary entry. The authoritative flat command tree SHALL include `wait-until-ready`, `wait-for-log-pattern`, `wait-for-exec`, `wait-for-result-marker`, `get-log-source`, `get-log-briefs`, `exec`, `ensure-stopped`, and `resolve-blocker`.

When distributed as a binary, the entry SHALL be `unity-puer-exec.exe` on Windows. The executable name (without extension) SHALL match the package name style. Agents and callers SHALL discover the binary by searching for `unity-puer-exec.exe` within the consuming Unity project's package cache, at the path `<PackageCache>/com.txcombo.unity-puer-exec@<version>/CLI~/unity-puer-exec.exe`.

#### Scenario: Agent discovers the CLI surface

- **WHEN** repository docs or help describe the CLI
- **THEN** `unity-puer-exec` is presented as the primary entry
- **AND** transitional aliases such as `unity-puer-session` are described only as compatibility paths, not as the authoritative surface
- **AND** transitional aliases remain thin adapters over the formal command behavior rather than separate feature-bearing command trees

#### Scenario: Agent discovers the binary CLI in a Unity project

- **WHEN** an agent needs to invoke the CLI within a Unity project that has the package installed via OpenUPM
- **THEN** the agent searches for `unity-puer-exec.exe` within the project directory
- **AND** the binary is located under `Library/PackageCache/com.txcombo.unity-puer-exec@<version>/CLI~/`
- **AND** the binary provides the same command surface as the Python source entry
