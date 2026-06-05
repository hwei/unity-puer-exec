## MODIFIED Requirements

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
