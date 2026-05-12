## MODIFIED Requirements

### Requirement: README conveys project vision and design philosophy

The `README.md` SHALL include a Vision section describing the goal of fully AI Agent-driven Unity development, and a Design Philosophy section describing the CLI-native, self-discoverable, minimal-primitives approach.

#### Scenario: Reader encounters the README for the first time

- **WHEN** a reader opens `README.md`
- **THEN** they encounter Vision and Design Philosophy before any installation instructions
- **AND** the Vision section describes the goal of AI Agent-driven Unity development without human IDE or Editor interaction
- **AND** the Design Philosophy section explains that the CLI is intentionally minimal and extensible through agent skills

### Requirement: README provides a language switcher near the top

Both `README.md` and `README.zh-CN.md` SHALL include a language switcher on the first line, before badges, linking to each other.

#### Scenario: Reader cannot read English

- **WHEN** a reader opens `README.md` and cannot read English
- **THEN** the language switcher is visible before any other content
- **AND** clicking the 中文 link opens `README.zh-CN.md`

#### Scenario: Reader cannot read Chinese

- **WHEN** a reader opens `README.zh-CN.md` and prefers English
- **THEN** the language switcher is visible before any other content
- **AND** clicking the English link opens `README.md`

### Requirement: README displays OpenUPM and Agentic AI badges

`README.md` SHALL display an OpenUPM badge linking to the package page and an Agentic AI Project badge.

#### Scenario: Reader views the README on GitHub or OpenUPM

- **WHEN** a reader views `README.md` on a Markdown renderer
- **THEN** the OpenUPM badge is visible and links to the OpenUPM package page for `com.txcombo.unity-puer-exec`
- **AND** the Agentic AI Project badge is visible

### Requirement: README.zh-CN.md is a complete Chinese translation

`README.zh-CN.md` SHALL be a complete translation of `README.md` with no sections omitted. Technical terms, package names, badge markup, and agent prompt content SHALL be preserved accurately.

#### Scenario: Chinese-speaking user reads the Chinese README

- **WHEN** a Chinese-speaking user opens `README.zh-CN.md`
- **THEN** all sections present in `README.md` are also present in Chinese
- **AND** agent prompts are translated into natural Chinese while preserving technical identifiers
