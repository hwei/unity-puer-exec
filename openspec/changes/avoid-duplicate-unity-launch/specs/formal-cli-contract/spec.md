## MODIFIED Requirements

### Requirement: `wait-until-ready` is the explicit readiness shortcut

`wait-until-ready` SHALL act as the explicit readiness-oriented command. In project-path mode it MAY discover or prepare Unity enough for normal use. In base-url mode it SHALL confirm readiness of the directly addressed service without taking ownership of Unity launch. When project-path mode detects an already-open or already-recovering editor for the same target project, it SHALL prefer recovering or reusing that project-scoped runtime instead of blindly starting a competing second Unity launch. If the CLI cannot safely recover or confirm ownership for the target project, it SHALL return a machine-readable non-success result instead of relying on a Unity-native duplicate-open dialog as the primary behavior.

#### Scenario: Project-scoped readiness is requested

- **WHEN** `wait-until-ready --project-path ...` is invoked
- **THEN** the command may discover an existing session or prepare Unity until the target becomes usable
- **AND** a successful result reports `result.status = "recovered"`

#### Scenario: Same project is already open during readiness recovery

- **WHEN** `wait-until-ready --project-path ...` targets a project that already has an open or recovering Unity Editor instance
- **THEN** the CLI reuses or waits for that project-scoped instance instead of starting a competing second launch
- **AND** the command does not treat a Unity-native duplicate-open dialog as the authoritative machine outcome

#### Scenario: Project-scoped launch ownership cannot be established safely

- **WHEN** the CLI cannot safely determine whether the addressed project is already owned by another Unity launch attempt or open editor instance
- **THEN** the command returns a machine-readable non-success result describing the launch-conflict condition
- **AND** the caller can branch on that result without scraping prose dialog text

### Requirement: `exec` is the primary work command

`exec` SHALL send JavaScript to the Unity-side execution service. It SHALL accept exactly one selector and exactly one script input source. In project-path mode it MAY implicitly prepare Unity enough to satisfy the request. In base-url mode it SHALL target an already chosen service without owning Unity launch. When project-path mode needs to prepare Unity, it SHALL follow the same duplicate-launch avoidance and project-scoped recovery rules as `wait-until-ready`.

#### Scenario: Project-scoped execution is requested

- **WHEN** `exec --project-path ...` is invoked with valid script input
- **THEN** the command may prepare Unity as needed for the execution request
- **AND** the command returns either `status = "completed"` or `status = "running"`

#### Scenario: Project-scoped exec encounters an already-open target project

- **WHEN** `exec --project-path ...` needs readiness work for a project that already has an open or recovering Unity Editor instance
- **THEN** the CLI applies the same project-scoped reuse or conflict behavior as `wait-until-ready`
- **AND** it does not initiate a blind second launch for the same project
