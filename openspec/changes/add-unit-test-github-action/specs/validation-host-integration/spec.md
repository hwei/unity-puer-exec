## ADDED Requirements

### Requirement: Real-host validation remains outside the default unit-test workflow
The repository SHALL keep real-host validation as a separate workflow surface from the default automated unit-test action. The default GitHub Actions unit-test workflow MUST NOT treat a skipped real-host test file as the mechanism for separating Unity-dependent validation from mocked/unit coverage.

#### Scenario: Maintainer reviews default CI coverage
- **WHEN** a maintainer inspects the repository's default automated unit-test workflow
- **THEN** the workflow does not include `tests/test_real_host_integration.py` in its selected test set
- **AND** the real-host validation path remains separately documented for machines that provide Unity Editor and `UNITY_PROJECT_PATH`
