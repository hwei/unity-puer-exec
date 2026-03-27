# Log Brief

## Purpose

Define the log-brief parsing model and `get-log-briefs` command. Log briefs provide compact, structured summaries of Unity Editor log entries within a caller-specified byte offset range, enabling agents to scan log activity without reading raw log files.
## Requirements
### Requirement: Log briefs summarize parsed log entries for an offset range

A log brief SHALL represent one parsed log entry (or one merged group of consecutive unrecognized entries) within a given log offset range. Each brief SHALL carry: a 1-based `index`, a `level` (`"info"`, `"warning"`, `"error"`, or `"unknown"`), a `line_count` (number of raw log lines covered), a `start_offset`, an `end_offset`, and a `text` field containing the first 100 characters of the entry's first line. Briefs with `level = "unknown"` SHALL have `text: null`.

#### Scenario: Brief covers a single parsed log entry

- **WHEN** a log entry is successfully parsed within the requested offset range
- **THEN** the brief reports the entry's level, its raw line span as `line_count`, its byte range as `start_offset` and `end_offset`, and up to 100 characters of the first line as `text`

#### Scenario: Brief covers a merged group of unrecognized entries

- **WHEN** two or more consecutive log lines within the offset range cannot be assigned to a known section or traceback pattern
- **THEN** those lines are collapsed into a single brief with `level = "unknown"`, `line_count` equal to the number of collapsed lines, `text: null`, and `start_offset` / `end_offset` spanning the entire group

### Requirement: Log parsing applies section-aware rules with documented fallback

The log-brief parser SHALL detect known Unity Editor log section markers and apply section-specific parsing rules within those sections. Outside known sections the parser SHALL fall back to traceback-based splitting. Lines that cannot be parsed by either rule SHALL be emitted as `"unknown"` briefs.

Known section rules:
- **C# compiler output** (`-----CompilerOutput:` … `-----EndCompilerOutput`): each line is one brief; level derived from `": error CS"` → `"error"`, `": warning CS"` → `"warning"`, otherwise `"info"`.
- **Runtime Unity log** (no section marker; entries separated by blank lines followed by a non-indented line): each traceback group is one brief; level derived from log-type markers in the entry header; default `"info"` when no marker is found.
- **Unknown / other sections**: emit merged `"unknown"` briefs as described above.

#### Scenario: Parser processes a C# compiler output section

- **WHEN** the offset range includes a `-----CompilerOutput:` section
- **THEN** each line within that section is emitted as a separate brief
- **AND** lines containing `": error CS"` receive `level = "error"`
- **AND** lines containing `": warning CS"` receive `level = "warning"`
- **AND** other lines receive `level = "info"`

#### Scenario: Parser processes a runtime Unity log entry with traceback

- **WHEN** the offset range contains a runtime log entry followed by indented traceback lines
- **THEN** the entry and its traceback lines are collapsed into one brief
- **AND** `line_count` reflects the total number of lines including traceback

#### Scenario: Parser encounters unrecognized log content

- **WHEN** consecutive lines in the offset range do not match any known section or traceback pattern
- **THEN** those lines are collapsed into a single `"unknown"` brief
- **AND** the brief's `line_count` accurately reflects how many lines were collapsed

### Requirement: get-log-briefs returns briefs for a caller-specified offset range

The CLI SHALL provide a `get-log-briefs` command that accepts a mandatory `--range` parameter and returns a JSON array of brief objects for the specified log offset range. `--range` SHALL accept both `START-END` (hyphen) and `START,END` (comma) forms. The command SHALL support optional `--levels` (comma-separated level names) and `--include` (comma-separated 1-based indices) filters. When both filters are supplied, the result SHALL be their union.

#### Scenario: Caller fetches all briefs for a range

- **WHEN** `get-log-briefs --range=12345-18920` is invoked
- **THEN** the command returns a JSON array of all briefs parsed within that range
- **AND** each brief includes `index`, `level`, `line_count`, `start_offset`, `end_offset`, and `text`

#### Scenario: Caller filters by level

- **WHEN** `get-log-briefs --range=12345-18920 --levels=error,warning` is invoked
- **THEN** the result includes only briefs with `level = "error"` or `level = "warning"`

#### Scenario: Caller selects specific indices

- **WHEN** `get-log-briefs --range=12345-18920 --include=3,5` is invoked
- **THEN** the result includes the briefs at 1-based positions 3 and 5 within the full parsed sequence for that range

#### Scenario: Caller supplies both --levels and --include

- **WHEN** `get-log-briefs --range=12345-18920 --levels=error --include=3` is invoked
- **THEN** the result includes all error-level briefs plus the brief at index 3, regardless of its level
- **AND** no brief appears more than once in the result

#### Scenario: Caller uses comma-separated range form

- **WHEN** `get-log-briefs --range=12345,18920` is invoked
- **THEN** the command behaves identically to `--range=12345-18920`

### Requirement: exec and wait-for-exec responses include log_range and brief_sequence

Every `exec` and `wait-for-exec` response SHALL include a top-level `log_range` object with `start` and `end` offset fields, and a top-level `brief_sequence` string. `log_range.start` SHALL be set to the log position at the time the CLI began observing the log for the request. `log_range.end` SHALL be set to the latest observed log tail at response time and SHALL never be absent. `brief_sequence` SHALL use a compact run encoding where each brief kind still uses the existing symbols (`"I"`, `"W"`, `"E"`, `"?"`), single-entry runs are emitted as the bare symbol, and repeated runs append a decimal count to the symbol. For example, `WI32E2I` represents `W`, then thirty-two `I` briefs, then two `E` briefs, then one `I` brief.

#### Scenario: exec returns with log activity during the operation

- **WHEN** `exec` returns any status response
- **THEN** the response includes `log_range.start`, `log_range.end`, and `brief_sequence`
- **AND** `brief_sequence` reflects log entries observed between `log_range.start` and `log_range.end`

#### Scenario: wait-for-exec returns an in-progress response

- **WHEN** `wait-for-exec` returns a non-terminal status such as `running` or `compiling`
- **THEN** the response includes `log_range` with `end` equal to the current log tail
- **AND** `brief_sequence` reflects log entries observed so far within the window

#### Scenario: brief_sequence remains observation-consistent across successive wait-for-exec calls

- **WHEN** a caller passes the same `log_range.start` as `--log-start-offset` to successive `wait-for-exec` calls
- **THEN** each later response remains consistent with the cumulative log activity since `log_range.start`
- **AND** callers can reconstruct the underlying observed brief kinds from the compact encoding without ambiguity

#### Scenario: exec returns with repeated log activity during the operation

- **WHEN** `exec` returns any status response with long repeated runs of the same brief kind
- **THEN** the response includes `log_range.start`, `log_range.end`, and compact encoded `brief_sequence`
- **AND** callers can still reconstruct the underlying brief kinds from the encoded form without ambiguity

### Requirement: log_offset and --include-log-offset are removed

The `log_offset` response field and the `--include-log-offset` flag SHALL be removed from all commands. Callers SHALL use `log_range.start` in place of `log_offset`.

#### Scenario: Caller previously used --include-log-offset

- **WHEN** a caller invokes `exec --include-log-offset`
- **THEN** the CLI reports a usage error
- **AND** the error message directs the caller to use `log_range.start` from the standard response instead

