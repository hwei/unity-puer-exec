# Spec Delta

## ADDED Requirements

### Requirement: Dialog body text is read from any readable descendant

The CLI SHALL read a dialog's message body text from any descendant window that carries
readable text, and SHALL traverse the window tree recursively rather than inspecting only
direct children. Window class SHALL NOT be the criterion for whether a descendant's text is
part of the body: the ScriptUpdater consent dialog is matched by its message text, and the
window class carrying that text is not stable across Editor versions.

#### Scenario: A message carried by a non-Static child is read

- **WHEN a dialog carries its message in a descendant whose window class is not `Static`
- **THEN the CLI reads that descendant's text as part of the dialog body
- **AND a catalog entry keyed on that text matches the dialog

#### Scenario: A message nested inside a container is read

- **WHEN a dialog's message lives one or more container levels below the dialog window
- **THEN the CLI reaches it and reads its text as part of the dialog body

#### Scenario: A plain Static-child dialog still reads

- **WHEN a dialog carries its message in a direct `Static` child
- **THEN the CLI reads that text as part of the dialog body, as before

### Requirement: An unreadable body is a named outcome, not an empty string

The CLI SHALL distinguish "the dialog has no readable text" from "the window enumeration
failed" when it reports a dialog body. A caller examining a dialog that produced no body text
SHALL be able to name which of those two conditions it observed, rather than receiving an
empty string that is indistinguishable from a dialog with no message.

#### Scenario: A textless dialog names that condition

- **WHEN the CLI inspects a dialog whose window tree carries no readable text
- **THEN the reported outcome names the absent-text condition
- **AND it is distinguishable from an enumeration failure

#### Scenario: An enumeration failure names that condition

- **WHEN the window enumeration itself fails while reading a dialog body
- **THEN the reported outcome names the enumeration-failure condition
- **AND it is not reported as a dialog with no message

#### Scenario: A fingerprint miss on readable text is still a mismatch

- **WHEN the CLI reads a non-empty dialog body and it matches no configured fingerprint
- **THEN the outcome is a text mismatch carrying the observed text
- **AND it is not reported as an unreadable body
