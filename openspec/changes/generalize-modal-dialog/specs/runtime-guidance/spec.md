## ADDED Requirements

### Requirement: Blocker guidance suggests the action legal for the reported blocker

The guidance matrix SHALL NOT suggest `resolve-blocker --action cancel` for a blocker type that cancel does not support. For the Safe Mode dialog it SHALL suggest `--action cancel`; for every other reported dialog — including save-scene dialogs and `unknown_modal_dialog` — it SHALL suggest the button-targeted form instead. Because candidate selection is driven by command and status alone, guidance for a blocker-bearing status SHALL carry the `when` condition that lets the caller pick the right form from the reported `blocker.type`, and SHALL NOT emit a concrete `argv` for the click form, since `hwnd` and button label come from the blocker payload rather than from the invocation arguments.

#### Scenario: Guidance for an unknown dialog suggests a click, not a cancel

- **WHEN** a command response reports `blocker.type = "unknown_modal_dialog"`
- **THEN** any `resolve-blocker` guidance entry suggests `--action click --hwnd --button`
- **AND** no suggested `argv` carries `--action cancel` for that blocker type

#### Scenario: Guidance for Safe Mode still suggests cancel

- **WHEN** a command response reports `blocker.type = "safe_mode_dialog"`
- **THEN** the `resolve-blocker` guidance entry suggests `--action cancel`
- **AND** the entry states that cancel is legal only for Safe Mode

#### Scenario: Click guidance names the payload fields it depends on

- **WHEN** a guidance entry suggests the button-targeted resolution form
- **THEN** its `when` text tells the caller to read `hwnd` and the button label from the reported blocker payload
- **AND** the entry omits `argv` rather than emitting an invocation with placeholder values the CLI cannot fill

### Requirement: Guidance covers button-targeted resolution failure statuses

Candidate selection SHALL remain driven by command name and status alone, so the button-targeted path's failure modes share the existing `resolution_failed` status and are distinguished only by `error`. The guidance matrix SHALL therefore provide a `situation` explanation for `(resolve-blocker, resolution_failed)` that covers both failure modes: a stale or foreign window handle, and a button label matching no enumerated button. Each explanation SHALL state what the caller should verify before retrying.

#### Scenario: Stale handle failure carries an explanation

- **WHEN** `resolve-blocker` returns `status = "resolution_failed"` with `error = "window_not_found"`
- **THEN** the response includes a `situation` string
- **AND** the `situation` text explains the stale-or-foreign-handle case and directs the caller to re-query blocker state for a current handle

#### Scenario: Unmatched label failure carries an explanation

- **WHEN** `resolve-blocker` returns `status = "resolution_failed"` with `error = "button_not_found"`
- **THEN** the response includes a `situation` string
- **AND** the `situation` text explains the no-matching-button case and directs the caller to re-read the `buttons` array from the blocker payload

#### Scenario: Situation does not depend on the error value

- **WHEN** the CLI builds guidance for a `resolve-blocker` `resolution_failed` response
- **THEN** the selected candidate is the one keyed by command and status alone
- **AND** the CLI does not inspect the `error` field to choose, reorder, or replace that candidate
