## MODIFIED Requirements

### Requirement: get-log-briefs returns briefs for a caller-specified offset range

The CLI SHALL provide a `get-log-briefs` command that accepts a mandatory `--range` parameter and returns a JSON array of brief objects for the specified log offset range. `--range` SHALL accept both `START-END` (hyphen) and `START,END` (comma) forms. The command SHALL support optional `--levels` (comma-separated level names) and `--indexes` (comma-separated 1-based indices) filters. `--include` SHALL remain accepted as a backward-compatible alias for `--indexes` with identical behavior. When both `--levels` and `--indexes` (or its `--include` alias) are supplied, the result SHALL be their union.

#### Scenario: Caller fetches all briefs for a range

- **WHEN** `get-log-briefs --range=12345-18920` is invoked
- **THEN** the command returns a JSON array of all briefs parsed within that range
- **AND** each brief includes `index`, `level`, `line_count`, `start_offset`, `end_offset`, and `text`

#### Scenario: Caller filters by level

- **WHEN** `get-log-briefs --range=12345-18920 --levels=error,warning` is invoked
- **THEN** the result includes only briefs with `level = "error"` or `level = "warning"`

#### Scenario: Caller selects specific indices with --indexes

- **WHEN** `get-log-briefs --range=12345-18920 --indexes=3,5` is invoked
- **THEN** the result includes the briefs at 1-based positions 3 and 5 within the full parsed sequence for that range

#### Scenario: Caller selects specific indices with the --include alias

- **WHEN** `get-log-briefs --range=12345-18920 --include=3,5` is invoked
- **THEN** the result is identical to invoking the same command with `--indexes=3,5`

#### Scenario: Caller supplies both --levels and --indexes

- **WHEN** `get-log-briefs --range=12345-18920 --levels=error --indexes=3` is invoked
- **THEN** the result includes all error-level briefs plus the brief at index 3, regardless of its level
- **AND** no brief appears more than once in the result

#### Scenario: Caller uses comma-separated range form

- **WHEN** `get-log-briefs --range=12345,18920` is invoked
- **THEN** the command behaves identically to `--range=12345-18920`

#### Scenario: Caller supplies invalid index syntax

- **WHEN** `get-log-briefs --range=12345-18920 --indexes=abc` is invoked
- **THEN** the CLI reports a usage error naming `--indexes`
- **AND** the error describes the accepted format as comma-separated 1-based brief indices (for example, `--indexes 3,5`) corresponding to `brief_sequence` positions

#### Scenario: Caller supplies conflicting --indexes and --include values

- **WHEN** `get-log-briefs --range=12345-18920 --indexes=3 --include=5` is invoked
- **THEN** the CLI reports a usage error rather than silently preferring either flag

### Requirement: Selected log briefs can include their complete text

The CLI SHALL accept `--full-text` on `get-log-briefs` only when `--indexes` (or its `--include` alias) supplies one or more explicit 1-based brief indices. Each selected brief SHALL retain its existing `text` preview and SHALL additionally include `full_text` containing the complete decoded raw log span assigned to that brief. Enabling full-text mode SHALL NOT cause unselected briefs to be returned.

#### Scenario: Caller retrieves one complete long log entry

- **WHEN** `get-log-briefs --range=12345-78901 --indexes=3 --full-text` selects a brief whose first line exceeds 100 characters
- **THEN** the selected brief's `text` remains the existing at-most-100-character preview
- **AND** `full_text` contains the complete entry text for brief index 3

#### Scenario: Caller selects multiple complete entries

- **WHEN** `get-log-briefs --range=12345-78901 --indexes=3,5 --full-text` is invoked
- **THEN** only briefs 3 and 5 are returned
- **AND** each returned brief includes its own complete `full_text`

#### Scenario: Full-text mode lacks explicit selection

- **WHEN** a caller invokes `get-log-briefs --full-text` without `--indexes` or `--include`
- **THEN** the CLI reports a usage error before returning log content
- **AND** the error names `--indexes` and explains that full-text retrieval requires explicit 1-based brief indices
