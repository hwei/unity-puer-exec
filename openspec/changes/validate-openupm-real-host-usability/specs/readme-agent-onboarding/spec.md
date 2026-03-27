## MODIFIED Requirements

### Requirement: Installation section provides a copy-pasteable agent prompt

The Installation section SHALL provide a prompt that users can give directly to an AI agent to install the package from OpenUPM. The prompt SHALL instruct the agent to auto-detect the Unity project path and ask if not found. The guidance SHALL also tell the agent to ask the user for proxy settings when the OpenUPM registry is unreachable instead of assuming the registry is always directly accessible.

#### Scenario: User wants to install via OpenUPM using an agent on a proxy-gated machine

- **WHEN** a user reads the Installation section and the machine cannot reach the OpenUPM registry directly
- **THEN** the guidance tells the agent to ask for proxy settings such as `HTTP_PROXY` / `HTTPS_PROXY`
- **AND** the prompt still references the OpenUPM registry URL
- **AND** the agent is not encouraged to loop indefinitely on direct access failures without asking the user for network configuration help
