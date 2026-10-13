## ADDED Requirements

### Requirement: A real-host refresh trigger is staged with a watched compile-triggering extension

The repository-owned real-host validation workflow SHALL stage a refresh trigger as a file whose extension the Editor's change signal watches, and SHALL reject a probe name outside that set before any Editor launch. A change signal that never becomes pending SHALL fail with the watched extensions and the observed `skipped_reason` named, so a mistyped probe is distinguishable from a genuine detection failure.

#### Scenario: A probe without a watched extension is rejected locally

- **WHEN** a real-host case stages a refresh trigger whose name does not end in a watched
  extension
- **THEN** the staging helper fails with the watched extensions named
- **AND** no Editor launch and no validation-host write occurs for that probe

#### Scenario: A change signal that never becomes pending names the cause

- **WHEN** a real-host case waits for a staged change to be observed as pending and the Editor
  never reports it as pending
- **THEN** the failure message names the watched extensions: C# sources, assembly definitions
  and references, and compiler response files
- **AND** it reports the observed `skipped_reason` from the last health payload

#### Scenario: A correctly staged probe still crosses a real refresh

- **WHEN** a real-host case stages a probe with a watched extension, waits for it to be observed
  as pending, and then runs `exec` against the host's control endpoint
- **THEN** the case proceeds unchanged and asserts the refresh disclosure on the terminal `exec`
  response