## MODIFIED Requirements

### Requirement: Direct base-url mode remains explicit

Base-url selector mode SHALL continue to target the caller-supplied endpoint directly. Direct mode SHALL NOT require project artifact validation and SHALL NOT imply Unity launch ownership. Base-url mode SHALL support `--refresh-before-exec`: because requesting a refresh does not launch Unity and does not change endpoint ownership, the refresh option is compatible with the direct-mode boundary. In base-url mode the post-refresh readiness settle SHALL re-probe the same caller-supplied endpoint rather than performing project-scoped re-acquisition.

#### Scenario: Caller supplies base-url

- **WHEN** a selector-driven command is invoked with `--base-url <url>`
- **THEN** the command targets that URL directly according to the existing direct-service command boundary
- **AND** it does not rewrite the endpoint from a project-local session artifact

#### Scenario: Base-url caller requests refresh-before-exec

- **WHEN** a caller invokes `exec --base-url <url> --refresh-before-exec`
- **THEN** the CLI performs the refresh against that endpoint instead of rejecting the option as project-only
- **AND** it settles the compile cycle by re-probing the same endpoint before running the user script
- **AND** it does not launch Unity or rewrite the endpoint from a session artifact

## ADDED Requirements

### Requirement: Refresh-before-exec is a single refresh-settle-execute lifecycle

For both selector modes, `--refresh-before-exec` SHALL define a single accepted-request lifecycle that performs the refresh, settles on the resulting compilation cycle, and then runs the caller's script in the resulting environment. The intermediate refreshing and compiling phases SHALL be non-terminal phases of the accepted exec request, and the server's `{"refreshed": true}` refresh confirmation SHALL NOT be presented as the caller's script result. The CLI SHALL make the next action explicit when the request is still refreshing or compiling so a caller does not mistake an intermediate phase for completion.

#### Scenario: Refresh-before-exec runs the script after settling

- **WHEN** a caller invokes `exec --refresh-before-exec` and the refresh triggers a compilation
- **THEN** the CLI settles on the compile cycle before running the caller's script
- **AND** the terminal response carries the script result, not the `{"refreshed": true}` refresh confirmation

#### Scenario: Caller observes an intermediate refreshing or compiling phase

- **WHEN** a refresh-before-exec request is still refreshing or compiling when a response is returned
- **THEN** the response represents a non-terminal accepted state rather than a terminal result
- **AND** the response makes the continuation path explicit so the caller can wait for the eventual script result
