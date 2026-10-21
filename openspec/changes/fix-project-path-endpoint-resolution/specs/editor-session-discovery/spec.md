# Spec Delta

## ADDED Requirements

### Requirement: A project path identifies its project regardless of spelling

The CLI SHALL treat a caller-supplied project path as the same project as the Editor's reported project path whenever both resolve to the same directory, including when the caller passes a path relative to its working directory, uses different separators or letter case, or uses a Windows short name. Endpoint ownership checks SHALL use this equality.

#### Scenario: A relative project path matches the Editor's absolute path

- **WHEN** a caller runs a project-mode command with `--project-path Project` from the directory containing `Project`
- **AND** the project's Editor reports its absolute project path in health
- **THEN** the CLI recognizes that endpoint as owned by the target project

#### Scenario: Another project's endpoint still does not match

- **WHEN** a ready endpoint reports a project path that resolves to a different directory than the caller's project path
- **THEN** the CLI does not treat that endpoint as owned by the target project

### Requirement: A reported session describes one Editor

Every `session` object a project-mode command reports SHALL take its `base_url`, `unity_pid`, and `project_path` from the same Editor. When the command could not identify the project's endpoint, it SHALL report `base_url` as `null`. It SHALL NOT substitute a default or scanned port that may belong to another project's Editor.

#### Scenario: Blocker query reports the project's own endpoint

- **WHEN** two Editors for different projects are running and an agent runs `get-blocker-state --project-path <A>`
- **THEN** the reported `session.base_url` is the endpoint published by project A's Editor
- **AND** the reported `session.unity_pid` is project A's Editor process id

#### Scenario: No publication yields no endpoint claim

- **WHEN** an agent runs `get-blocker-state` for a project with no endpoint publication
- **THEN** the reported `session.base_url` is `null`
- **AND** the command does not report the default control port as the project's endpoint
