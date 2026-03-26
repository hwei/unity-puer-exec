## Purpose
TBD - created by archiving change improve-readme-for-openupm-release. Update Purpose after archive.

## Requirements

### Requirement: README conveys project vision and design philosophy
The `ReadMe.md` SHALL include a Vision section describing the goal of fully AI Agent-driven Unity development, and a Design Philosophy section describing the CLI-native, self-discoverable, minimal-primitives approach.

#### Scenario: Reader encounters the README for the first time
- **WHEN** a reader opens `ReadMe.md`
- **THEN** they encounter Vision and Design Philosophy before any installation instructions
- **AND** the Vision section describes the goal of AI Agent-driven Unity development without human IDE or Editor interaction
- **AND** the Design Philosophy section explains that the CLI is intentionally minimal and extensible through agent skills

### Requirement: README provides a language switcher near the top
Both `ReadMe.md` and `ReadMe.zh-CN.md` SHALL include a language switcher on the first line, before badges, linking to each other.

#### Scenario: Reader cannot read English
- **WHEN** a reader opens `ReadMe.md` and cannot read English
- **THEN** the language switcher is visible before any other content
- **AND** clicking the 中文 link opens `ReadMe.zh-CN.md`

#### Scenario: Reader cannot read Chinese
- **WHEN** a reader opens `ReadMe.zh-CN.md` and prefers English
- **THEN** the language switcher is visible before any other content
- **AND** clicking the English link opens `ReadMe.md`

### Requirement: README displays OpenUPM and Agentic AI badges
`ReadMe.md` SHALL display an OpenUPM badge linking to the package page and an Agentic AI Project badge.

#### Scenario: Reader views the README on GitHub or OpenUPM
- **WHEN** a reader views `ReadMe.md` on a Markdown renderer
- **THEN** the OpenUPM badge is visible and links to the OpenUPM package page for `com.txcombo.unity-puer-exec`
- **AND** the Agentic AI Project badge is visible

### Requirement: Installation section provides a copy-pasteable agent prompt
The Installation section SHALL provide a prompt that users can give directly to an AI agent to install the package from OpenUPM. The prompt SHALL instruct the agent to auto-detect the Unity project path and ask if not found.

#### Scenario: User wants to install via OpenUPM using an agent
- **WHEN** a user reads the Installation section
- **THEN** they find a quoted prompt they can copy and give to their agent
- **AND** the prompt references the OpenUPM registry URL
- **AND** the prompt instructs the agent to ask for the project path if it cannot be found automatically

### Requirement: Usage section explains CLI discovery by package name
The Usage section SHALL state that the CLI binary is inside the package at `CLI~/unity-puer-exec.exe` and that agents can find it by searching for the package `com.txcombo.unity-puer-exec` within the Unity project.

#### Scenario: Agent reads the usage guidance to find the CLI
- **WHEN** a user passes the usage guidance to their agent
- **THEN** the agent has enough information to locate `unity-puer-exec.exe` within the Unity project without a hardcoded full path

### Requirement: Usage section provides two concrete example prompts
The Usage section SHALL include at least two example prompts: one for a simple scene operation and one for a multi-step code change, compile cycle, and verification workflow.

#### Scenario: User wants to perform a simple Unity scene operation
- **WHEN** a user reads the simple scene operation example
- **THEN** they find a prompt they can adapt to their own scene
- **AND** the prompt does not include an instruction to verify the result (human verifies visually)

#### Scenario: User wants to perform a code change with compile and verify
- **WHEN** a user reads the code change example
- **THEN** they find a prompt that covers writing code, handling compilation, and verifying the result
- **AND** verification is explicitly part of the example goal

### Requirement: README includes a Solidifying Skills section
The README SHALL include a section that explains the pattern of repeated agent workflows and JS scripts, and provides a specific opening prompt for starting a skill design conversation with an agent.

#### Scenario: User notices they keep asking the agent to repeat the same Unity operations
- **WHEN** a user reads the Solidifying Skills section
- **THEN** they understand the scenario of repeated JS scripts and re-explained workflows
- **AND** they find a quoted opening prompt they can give their agent to begin a skill design discussion

### Requirement: ReadMe.zh-CN.md is a complete Chinese translation
`ReadMe.zh-CN.md` SHALL be a complete translation of `ReadMe.md` with no sections omitted. Technical terms, package names, badge markup, and agent prompt content SHALL be preserved accurately.

#### Scenario: Chinese-speaking user reads the Chinese README
- **WHEN** a Chinese-speaking user opens `ReadMe.zh-CN.md`
- **THEN** all sections present in `ReadMe.md` are also present in Chinese
- **AND** agent prompts are translated into natural Chinese while preserving technical identifiers
