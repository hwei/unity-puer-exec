## MODIFIED Requirements

### Requirement: Selector-driven commands use mutually exclusive addressing

Selector-driven commands SHALL accept exactly one of `--project-path` or `--base-url`. Supplying both MUST be treated as a usage error. Project-path resolution SHALL follow the repository-wide deterministic resolution order: explicit `--project-path` argument, then `UNITY_PROJECT_PATH` environment variable, then exe origin inference from `sys.argv[0]`, then cwd fallback. When exe origin inference succeeds, selector-driven commands SHALL treat the inferred path as though `--project-path` had been supplied, so callers are not required to provide an explicit project path when the exe is installed inside the target Unity project.

#### Scenario: Caller supplies both selectors

- **WHEN** a selector-driven command receives both `--project-path` and `--base-url`
- **THEN** the command reports a usage error
- **AND** machine-readable output surfaces `address_conflict` when structured output is produced

#### Scenario: Caller supplies neither selector but exe inference succeeds

- **WHEN** a selector-driven command receives neither `--project-path` nor `--base-url`
- **AND** exe origin inference resolves a valid Unity project root
- **THEN** the command operates in project-path mode using the inferred path
- **AND** the behavior is equivalent to having supplied `--project-path` with the inferred value
