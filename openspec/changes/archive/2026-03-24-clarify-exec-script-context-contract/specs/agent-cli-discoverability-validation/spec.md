## ADDED Requirements

### Requirement: Exec script context documents guaranteed fields and supported path derivation
The CLI SHALL document the guaranteed `ctx` fields for `exec` scripts and SHALL direct users toward supported Unity APIs when project-local paths are needed.

#### Scenario: Contributor writes a Prompt B style host-edit script
- **WHEN** a contributor authors an `exec` script that needs request metadata and host-project file access
- **THEN** the published guidance identifies which `ctx` fields are guaranteed
- **AND** the guidance does not imply unsupported fields such as `ctx.project_path` are available unless the runtime truly guarantees them
- **AND** the guidance points to a supported way to derive project-local paths
- **AND** Prompt B validation can compare whether task scripts stop assuming unsupported `ctx` fields
