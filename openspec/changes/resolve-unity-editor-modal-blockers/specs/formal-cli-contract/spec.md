## ADDED Requirements

### Requirement: `resolve-blocker` dismisses supported modal blockers explicitly

The CLI SHALL expose a dedicated `resolve-blocker` command for project-scoped Windows workflows. The first version SHALL require `--project-path` and SHALL support only `--action cancel`.

#### Scenario: Caller resolves a supported blocker with cancel

- **WHEN** `resolve-blocker --project-path ... --action cancel` is invoked while exactly one supported blocker dialog is present
- **THEN** the CLI attempts the targeted cancel action for that dialog
- **AND** success returns `status = "completed"`
- **AND** `result.status = "resolved"`
- **AND** `result.action = "cancel"`
- **AND** `result.blocker.type` identifies the dismissed blocker

#### Scenario: Caller invokes resolution when no supported blocker is present

- **WHEN** `resolve-blocker --project-path ... --action cancel` is invoked and no supported blocker dialog is currently detected
- **THEN** the CLI returns `status = "no_supported_blocker"`
- **AND** it does not perform a fallback UI action against unrelated windows

#### Scenario: Caller invokes resolution when multiple supported blockers are present

- **WHEN** `resolve-blocker --project-path ... --action cancel` is invoked and more than one supported blocker dialog is detected
- **THEN** the CLI returns `status = "resolution_failed"`
- **AND** `error = "multiple_supported_blockers"`
- **AND** it does not act on any of the matching dialogs

#### Scenario: Caller invokes resolution on an unsupported surface

- **WHEN** `resolve-blocker` is invoked without `--project-path` or on a non-Windows platform
- **THEN** the CLI returns `status = "unsupported_operation"`
- **AND** `error = "windows_project_path_required"`

### Requirement: Resolution confirms the dialog closes before reporting success

The first version SHALL confirm the targeted dialog disappears before returning a successful resolution result.

#### Scenario: Cancel action is issued but dialog disappearance is not confirmed

- **WHEN** the CLI issues the targeted `cancel` action for a supported blocker but the dialog still appears present after the fixed internal confirmation timeout
- **THEN** the CLI returns `status = "resolution_failed"`
- **AND** `error = "click_not_confirmed"`

### Requirement: Resolution preserves blocked exec ownership

Resolving a blocker SHALL NOT resubmit or replace the original blocked exec request. The caller SHALL continue waiting on the original request if it still wants the exec outcome.

#### Scenario: Caller resolves a blocker for a blocked exec request

- **WHEN** `resolve-blocker --action cancel` succeeds for a blocker that interrupted an existing exec request
- **THEN** the CLI does not submit a new exec request automatically
- **AND** the caller can continue with `wait-for-exec --request-id ...`
