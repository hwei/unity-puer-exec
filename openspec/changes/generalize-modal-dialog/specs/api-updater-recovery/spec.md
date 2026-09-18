## MODIFIED Requirements

### Requirement: Agents never see this dialog as modal_blocked

The ScriptUpdater consent dialog SHALL NOT be surfaced as `status = "modal_blocked"` and SHALL NOT require `resolve-blocker`. Save-scene dialogs keep their stable `modal_blocked` types but lose automatic cancel resolution, and any other Editor dialog that blocks exec is still surfaced as `modal_blocked` with `blocker.type = "unknown_modal_dialog"`.

#### Scenario: exec timeout coincides with the consent dialog

- **WHEN** `exec` or `wait-for-exec` would otherwise inspect modal blockers because the request is running or timed out
- **AND** the only supported dialog is the ScriptUpdater consent dialog
- **THEN** the CLI auto-declines it
- **AND** the response is not `modal_blocked` with an API-updater blocker type

## ADDED Requirements

### Requirement: ScriptUpdater recovery is unaffected by dialog generalization

Generalizing modal dialog detection SHALL NOT change ScriptUpdater consent recovery. The consent dialog SHALL continue to be matched by its message body rather than its title, SHALL continue to be auto-declined by activating the No button, and SHALL NOT be reclassified as `unknown_modal_dialog` or reported as a blocker requiring `resolve-blocker`.

#### Scenario: Consent dialog is not reclassified as unknown

- **WHEN** the CLI inspects modal blockers for an Editor whose only matching dialog is the ScriptUpdater consent dialog
- **THEN** the dialog is auto-declined by activating No
- **AND** it is not reported as `unknown_modal_dialog`

#### Scenario: Consent dialog remains absent from blocker listings

- **WHEN** a caller queries blocker state while the ScriptUpdater consent dialog is visible
- **AND** no other blocking dialog is present
- **THEN** the query reports no blocker
- **AND** the consent dialog does not appear in any blocker payload
