# Spec Delta

## ADDED Requirements

### Requirement: A case asserts the product's report for a dialog the product dismisses

When a real-host case stages a dialog that the CLI dismisses automatically, the case SHALL
assert the product's own report of that dismissal rather than inspecting the dialog's window
state after the command. A post-command window read SHALL NOT be the evidence for an
auto-recovered dialog, because the command under test is what removes the dialog.

#### Scenario: Auto-recovered dialog is asserted through the product report

- **WHEN a real-host case stages the ScriptUpdater consent dialog and runs a CLI command
- **THEN the case asserts the command's `warning = "api_updater_declined"` and its
  `warning_detail`
- **AND it does not assert that the dialog is still visible after the command

#### Scenario: An absent dialog is not reported as an untriggered one

- **WHEN a post-command observation finds no auto-recovered dialog
- **AND the same command reported that it declined one
- **THEN the case treats the dialog as triggered and dismissed
- **AND it does not skip with a "could not be triggered" reason

### Requirement: A case may observe a dialog the product leaves alone

When a real-host case stages a dialog the CLI does not dismiss automatically, the case SHALL
continue to assert on the observed dialog. Such a dialog SHALL NOT be treated as an
auto-recovered dialog merely because a CLI command ran before the observation.

#### Scenario: Catalog dialogs are still observed directly

- **WHEN a real-host case stages a save-scene, modified-scene, or unknown prompt dialog
- **AND runs a CLI command before inspecting window state
- **THEN the case observes the staged dialog and asserts on its payload
- **AND no guard treats that observation as a race

### Requirement: The suite structure is guarded against reintroducing the race

The repository SHALL carry a guard that fails when a real-host case combines an auto-recovered
dialog with a post-command window read. The guard SHALL derive its inventory from the real-host
suite source rather than from a hand-maintained list, so a new case is covered without a second
place to update.

#### Scenario: A reintroduced race fails the guard

- **WHEN a real-host case stages an auto-recovered dialog and then reads window state after a
  CLI command
- **THEN the guard reports that case by name
- **AND the default mocked suite fails without needing an Editor

#### Scenario: A sound post-command observation passes the guard

- **WHEN a real-host case stages a dialog the product does not dismiss and reads window state
  after a command
- **THEN the guard reports no violation for that case
