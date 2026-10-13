## ADDED Requirements

### Requirement: get-log-briefs is selector-driven

The `get-log-briefs` command SHALL accept exactly one of `--project-path` or `--base-url`, like
the other selector-driven commands. In base-url mode it SHALL reject `--unity-log-path` with a
project-mode-only usage error, and supplying both selectors SHALL be an `address_conflict` usage
error.

#### Scenario: Base-url caller supplies a project-only log path

- **WHEN** `get-log-briefs --base-url <url> --unity-log-path <path> --range <start>-<end>` is invoked
- **THEN** the command reports a usage error stating `--unity-log-path` is only valid with `--project-path`

#### Scenario: Base-url and project-path are supplied together

- **WHEN** `get-log-briefs` receives both `--project-path` and `--base-url`
- **THEN** the command reports an `address_conflict` usage error

### Requirement: Base-url log observation uses the endpoint-named path

In base-url mode the CLI SHALL resolve every log-related operation from the addressed endpoint's
reported console log path: the `log_range` a completed response advertises and the source
`get-log-briefs` parses. It SHALL use the platform default path only when the endpoint reports
none, and SHALL NOT transfer log content over the network. When no source resolves at all,
`get-log-briefs` SHALL report `no_observation_target`.

#### Scenario: A base-url response's offsets and briefs share the Editor-named path

- **WHEN** a base-url command completes and the endpoint reports a console log path
- **THEN** the advertised `log_range` is captured from that path
- **AND** `get-log-briefs --base-url` parses that same path for the advertised range

#### Scenario: Base-url caller reads briefs from the reported log path

- **WHEN** `get-log-briefs --base-url <url> --range <start>-<end>` is invoked and the endpoint's health response reports a console log path
- **THEN** the command parses that log file locally and returns the briefs for the range
- **AND** it does not require a project session artifact

#### Scenario: Base-url caller has no observable log source

- **WHEN** `get-log-briefs --base-url <url> --range <start>-<end>` is invoked and the endpoint reports no console log path and no default log file exists
- **THEN** the command reports `no_observation_target`
- **AND** it does not parse a path that does not exist
