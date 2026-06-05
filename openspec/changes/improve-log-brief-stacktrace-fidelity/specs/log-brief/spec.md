## MODIFIED Requirements

### Requirement: Log parsing applies section-aware rules with documented fallback

The log-brief parser SHALL detect known Unity Editor log section markers and apply section-specific parsing rules within those sections. Outside known sections the parser SHALL fall back to traceback-based splitting. Lines that cannot be parsed by either rule SHALL be emitted as `"unknown"` briefs.

Known section rules:
- **C# compiler output** (`-----CompilerOutput:` … `-----EndCompilerOutput`): each line is one brief; level derived from `": error CS"` → `"error"`, `": warning CS"` → `"warning"`, otherwise `"info"`.
- **Runtime Unity log** (no section marker): an entry SHALL begin at a non-blank, non-indented line and SHALL continue until the next entry boundary. A new entry boundary is a non-blank, non-indented line that follows a blank line; a non-blank, non-indented line that is **not** preceded by a blank line is a continuation of the current entry (e.g. a Unity stack-frame line, which begins at column 0). A blank line followed by a `(Filename: …)` footer is consumed into the current entry as its trailing footer rather than treated as a boundary. The entry level SHALL be derived from log-type markers in the entry's first (header) line only; continuation lines SHALL NOT change the level. Default level is `"info"` when no marker is found.
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
- **THEN** the header, the stack-frame lines, and the footer are collapsed into a single brief whose level comes from the header line
- **AND** the brief's `line_count` includes the header, every stack-frame line, and the footer, but excludes the blank separator before the next entry

#### Scenario: Parser keeps consecutive non-indented lines without a blank separator in one brief

- **WHEN** two or more non-blank, non-indented lines appear consecutively with no blank line between them
- **THEN** they are collapsed into a single brief whose level comes from the first line
- **AND** a non-indented line is only treated as a new entry when it is preceded by a blank line

#### Scenario: Parser encounters unrecognized log content

- **WHEN** consecutive lines in the offset range do not match any known section or traceback pattern
- **THEN** those lines are collapsed into a single `"unknown"` brief
- **AND** the brief's `line_count` accurately reflects how many lines were collapsed

## ADDED Requirements

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
