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
- **Runtime Unity log** (no section marker): an entry SHALL begin at a non-blank, non-indented line and SHALL continue until the next entry boundary. A new entry boundary is a non-blank, non-indented line that follows a blank line; a non-blank, non-indented line that is **not** preceded by a blank line is a continuation of the current entry (e.g. a Unity stack-frame line, which begins at column 0). A blank line followed by a `(Filename: …)` footer is consumed into the current entry as its trailing footer rather than treated as a boundary.

  The entry level SHALL be derived as follows, in priority order:
  1. **Header marker** — if the entry's first (header) line begins with a log-type marker (`[Error]`/`[Exception]` → `"error"`, `[Warning]` → `"warning"`), that level is used.
  2. **Unity logging stack frame** — otherwise, if any line in the entry is a Unity logging API frame fully qualified as `UnityEngine.Debug` followed by a `:` or `.` separator and a `Log*` method, the level is derived from that method: `LogError`, `LogException`, `LogAssertion` (and their `*Format` variants) → `"error"`; `LogWarning` (and `LogWarningFormat`) → `"warning"`; `Log`, `LogFormat` → `"info"`.
  3. **Exception-signature header** — otherwise, if the header line matches an uncaught-exception signature (a leading `<Type>Exception:` token), the level is `"error"`.
  4. **Default** — otherwise the level is `"info"`.

  The stack-frame match SHALL be anchored to the fully-qualified `UnityEngine.Debug` type token so that arbitrary message text or user-defined frames (e.g. a user type named `Debug` or a message containing the word "Error") do not change the level. Continuation lines SHALL NOT change the level except through this anchored Unity logging frame match. When stack-trace logging is disabled, no Unity logging frame is present and the entry falls through to the default `"info"`; that degraded regime is signalled separately (see the degraded-briefs requirement) and is not addressed by this rule.
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

#### Scenario: Parser groups a Unity Debug.Log entry with its stack frames and footer

- **WHEN** the offset range contains a runtime header line followed by non-indented Unity stack-frame lines, a blank line, and a `(Filename: … Line: N)` footer
- **THEN** the header, the stack-frame lines, and the footer are collapsed into a single brief
- **AND** the brief's `line_count` includes the header, every stack-frame line, and the footer, but excludes the blank separator before the next entry

#### Scenario: Parser derives error level from the Debug:LogError stack frame on a bare header

- **WHEN** a runtime entry has a header line with no `[Error]`/`[Warning]` marker and the entry contains a `UnityEngine.Debug:LogError (object)` stack frame
- **THEN** the brief receives `level = "error"`
- **AND** the same rule maps a `UnityEngine.Debug:LogWarning` frame to `level = "warning"` and a `UnityEngine.Debug:Log` frame to `level = "info"`

#### Scenario: Parser does not derive level from message text or non-Unity frames

- **WHEN** a runtime entry has a bare header and contains no `UnityEngine.Debug:Log*` frame, even if its text contains the word "Error" or a user-defined frame such as `MyGame.Debug:LogError`
- **THEN** the brief level is not flipped by that text and falls through to the default `"info"` (or to the exception-signature rule when the header is an uncaught-exception line)

#### Scenario: Parser classifies an uncaught-exception header as error

- **WHEN** a runtime entry header matches an uncaught-exception signature such as `NullReferenceException: Object reference not set to an instance of an object`
- **THEN** the brief receives `level = "error"`

#### Scenario: Parser keeps consecutive non-indented lines without a blank separator in one brief

- **WHEN** two or more non-blank, non-indented lines appear consecutively with no blank line between them
- **THEN** they are collapsed into a single brief whose level is derived by the priority order above
- **AND** a non-indented line is only treated as a new entry when it is preceded by a blank line

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

### Requirement: Observation surfaces signal degraded briefs when stack-trace logging is disabled

The observation surface SHALL signal a degraded condition when Unity stack-trace logging is disabled, because the runtime traceback grouping rule depends on Unity emitting stack traces: entries are delimited by the blank line that follows each stack trace and its `(Filename: …)` footer. When stack-trace logging is disabled (`StackTraceLogType.None`), `Debug.Log` output collapses into bare back-to-back lines that the grouping rule cannot reliably delimit, so brief counts and `brief_sequence` become misleading.

The degraded condition SHALL be detected via the Unity Editor API on the C# side, NOT via a structural heuristic in the Python parser. The Unity Editor log normally contains back-to-back non-indented native lines (assembly reload, domain-reload profiling, build output) even when stack traces are enabled, so a heuristic that infers "stack traces disabled" from the absence of footers or stack frames would produce false positives.

The C# server SHALL report the current `StackTraceLogType` for `LogType.Log`, `LogType.Warning`, and `LogType.Error` in its exec / wait-for-exec response. The condition SHALL be treated as degraded when **any** of those three is `None`.

When the response reports a degraded condition, the `exec` and `wait-for-exec` flows SHALL set `brief_sequence` to a documented sentinel value (distinct from any real brief encoding) and SHALL include an operator-facing hint that stack-trace logging must be enabled (`ScriptOnly` or `Full`) for log briefs to be meaningful. In the degraded state the sentinel supersedes the observation-consistency / prefix-extension property that normal `brief_sequence` values guarantee across successive calls: a degraded sentinel signals "briefs are not trustworthy" and is not a prefix extension of any prior sequence.

The standalone `get-log-briefs --range` command has no C# context and SHALL NOT attempt heuristic detection; its documented contract notes that brief output is unreliable when stack-trace logging is disabled.

#### Scenario: exec reports degraded briefs when stack-trace logging is disabled

- **WHEN** `exec` or `wait-for-exec` runs and the C# response reports `StackTraceLogType.None` for any of `LogType.Log`, `LogType.Warning`, or `LogType.Error`
- **THEN** the response's `brief_sequence` is set to the documented degraded sentinel
- **AND** the response includes a hint directing the operator to enable `ScriptOnly`/`Full` stack-trace logging

#### Scenario: exec reports normal briefs when stack-trace logging is enabled

- **WHEN** `exec` or `wait-for-exec` runs and the C# response reports a non-`None` `StackTraceLogType` for all of `LogType.Log`, `LogType.Warning`, and `LogType.Error`
- **THEN** `brief_sequence` is computed normally from the parsed briefs
- **AND** no stack-trace hint is added

#### Scenario: Standalone get-log-briefs does not heuristically infer the setting

- **WHEN** `get-log-briefs --range` is invoked
- **THEN** the parser emits briefs from the raw byte range without attempting to detect whether stack-trace logging is enabled

