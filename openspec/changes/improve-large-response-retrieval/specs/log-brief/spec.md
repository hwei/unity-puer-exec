## ADDED Requirements

### Requirement: Selected log briefs can include their complete text

The CLI SHALL accept `--full-text` on `get-log-briefs` only when `--include` supplies one or more explicit 1-based brief indices. Each selected brief SHALL retain its existing `text` preview and SHALL additionally include `full_text` containing the complete decoded raw log span assigned to that brief. Enabling full-text mode SHALL NOT cause unselected briefs to be returned.

#### Scenario: Caller retrieves one complete long log entry

- **WHEN** `get-log-briefs --range=12345-78901 --include=3 --full-text` selects a brief whose first line exceeds 100 characters
- **THEN** the selected brief's `text` remains the existing at-most-100-character preview
- **AND** `full_text` contains the complete entry text for brief index 3

#### Scenario: Caller selects multiple complete entries

- **WHEN** `get-log-briefs --range=12345-78901 --include=3,5 --full-text` is invoked
- **THEN** only briefs 3 and 5 are returned
- **AND** each returned brief includes its own complete `full_text`

#### Scenario: Full-text mode lacks explicit selection

- **WHEN** a caller invokes `get-log-briefs --full-text` without `--include`
- **THEN** the CLI reports a usage error before returning log content
- **AND** the error explains that full-text retrieval requires explicit 1-based brief indices

### Requirement: Full-text spans use exact byte boundaries

The log-brief parser SHALL calculate `start_offset` and `end_offset` from the raw log bytes so the interval `[start_offset, end_offset)` identifies the exact byte span assigned to each brief, including entries containing multibyte UTF-8 text. `full_text` SHALL be produced by decoding that exact span as UTF-8 with replacement for malformed sequences.

#### Scenario: Selected entry contains multibyte Unicode text

- **WHEN** a selected log entry contains multibyte UTF-8 characters
- **THEN** its offsets delimit the exact raw byte span rather than character-count approximations
- **AND** `full_text` contains the complete decoded entry without cutting a valid multibyte character

### Requirement: Default log-brief output remains compact

When `--full-text` is absent, `get-log-briefs` SHALL preserve the existing brief response shape and 100-character `text` preview behavior, and SHALL NOT add `full_text`.

#### Scenario: Caller uses the existing brief workflow

- **WHEN** a caller invokes `get-log-briefs --range=12345-78901` without `--full-text`
- **THEN** each returned brief uses the existing compact fields
- **AND** no brief contains `full_text`
