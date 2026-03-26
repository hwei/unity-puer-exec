## ADDED Requirements

### Requirement: Default unit tests do not require repository-local Unity project configuration

The repository SHALL keep the default GitHub Actions unit-test suite independent from repository-local `.env` contents and process-level `UNITY_PROJECT_PATH` configuration.

#### Scenario: GitHub-hosted unit tests run without Unity project configuration

- **WHEN** the default `Unit Tests` workflow runs on a GitHub-hosted runner without `.env` and without `UNITY_PROJECT_PATH`
- **THEN** the selected unit tests complete without failing on missing real-project configuration
- **AND** any Unity-project-dependent validation remains outside the default unit-test workflow boundary
