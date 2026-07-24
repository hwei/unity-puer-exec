## MODIFIED Requirements

### Requirement: The CLI has one primary entry and flat command tree

The formal CLI SHALL use `unity-puer-exec` as its single primary entry. The authoritative flat command tree SHALL include `wait-for-log-pattern`, `wait-for-exec`, `wait-for-result-marker`, `wait-for-compile`, `get-log-source`, `get-log-briefs`, `exec`, `ensure-stopped`, `resolve-blocker`, `get-blocker-state`, `get-compile-errors`, and `get-compile-warnings`.

This tree SHALL be the single declaration of the CLI's command set. The invocable command surface, the per-command help tiers, the top-level command summary, and runtime guidance coverage SHALL all be defined over exactly this set, so a command cannot be invocable while being absent from help or guidance.

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

#### Scenario: Invocable set and documented set agree

- **WHEN** the set of commands the CLI accepts is compared with the set that answers help tiers, the set summarized in top-level help, and the set covered by runtime guidance
- **THEN** all four sets are the same set
- **AND** no command is invocable while absent from any of them

## ADDED Requirements

### Requirement: Every command in the flat command tree answers every help tier

Each command in the authoritative flat command tree SHALL answer `--help`, `--help-args`, and `--help-status` with rendered help content. A command SHALL NOT reject a help tier as an unrecognized argument, because a caller that discovered the command from the CLI's own usage output has no other way to learn its arguments or statuses.

#### Scenario: Every command answers the help tiers

- **WHEN** a caller invokes `<command> --help`, `<command> --help-args`, or `<command> --help-status` for any command in the flat command tree
- **THEN** the CLI renders the corresponding help content
- **AND** exits successfully

#### Scenario: Compile-message commands answer help like any other command

- **WHEN** a caller invokes `get-compile-errors --help` or `get-compile-warnings --help`
- **THEN** the CLI renders command help rather than reporting `--help` as an unrecognized argument

#### Scenario: Every command appears in top-level help

- **WHEN** a caller invokes `unity-puer-exec --help`
- **THEN** every command in the flat command tree appears in the command summary
- **AND** a caller can reach each command's own help from that summary
