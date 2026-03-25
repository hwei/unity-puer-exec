## MODIFIED Requirements

### Requirement: Exec Quick Start surfaces ctx-contract limitation before first script attempt

The `exec --help` Quick Start SHALL include a brief warning that the script `ctx` object is intentionally narrow, so agents and users encounter the limitation before writing their first script rather than only after consulting `--help-args`.

#### Scenario: Agent reads exec Quick Start before authoring a script

- **WHEN** an agent or user reads `exec --help` to learn how to write their first script
- **THEN** the Quick Start text states that `ctx` only guarantees `request_id` and `globals`
- **AND** the text points to `--help-args` or the `derive-project-path-from-unity-api` example for project-path derivation
- **AND** the agent does not need to discover the ctx limitation by trial and error or by separately reading `--help-args`
