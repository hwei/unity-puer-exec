# Spec Delta

## MODIFIED Requirements

### Requirement: Play settles pending code before entering play mode

When a compile-triggering change is pending, `play` SHALL refresh and settle the compile cycle before entering play mode, so a play session never starts on code that omits a pending change. If compilation fails, `play` SHALL NOT enter play mode and SHALL return the `unity_compile_error` status and exit code that `exec` uses. The refresh disclosure in a play result SHALL be the decision that resolved the pre-play settle, so a caller can tell a settle that resolved because the service suppressed a candidate it had already refreshed from a settle that never saw a pending change.

#### Scenario: Pending change compiles cleanly

- **WHEN** an agent runs `play` with a compile-triggering change pending
- **THEN** the command refreshes and waits for compilation to settle before requesting play mode
- **AND** the result discloses that a refresh ran

#### Scenario: Pending change fails to compile

- **WHEN** an agent runs `play` and the pending change has compile errors
- **THEN** the Editor stays in edit mode
- **AND** the command returns `unity_compile_error` with exit code 23 and inline compile errors

#### Scenario: A settle resolved by suppression discloses the resolving decision

- **WHEN** a `play` pre-settle dispatched a refresh for a candidate
- **AND** a later poll resolved the settle by suppressing that candidate as content already handed to
  a dispatched refresh
- **THEN** the play result's refresh disclosure names the suppressed paths
- **AND** it reports the resolving decision rather than only the dispatching one

#### Scenario: A dispatch and its suppression are both visible

- **WHEN** a `play` pre-settle dispatched a refresh and then resolved on a suppressed decision
- **THEN** the play result discloses that a refresh ran
- **AND** it also discloses the paths the resolving decision suppressed

#### Scenario: A settle that never dispatched discloses no refresh

- **WHEN** a `play` pre-settle found no compile-triggering change pending
- **AND** the resolving decision suppressed no paths
- **THEN** the play result discloses no refresh, exactly as it does today
- **AND** it reports no suppressed paths

#### Scenario: A suppression on the first poll is disclosed even without a dispatch

- **WHEN** a `play` pre-settle's first poll resolves on a decision that dispatched nothing in this
  invocation but suppressed one or more paths (for example content an earlier `exec` already
  handed to a dispatched refresh)
- **THEN** the play result carries a refresh disclosure naming those suppressed paths
- **AND** that disclosure reports that no refresh was triggered

#### Scenario: The disclosure stays additive

- **WHEN** a play result carries a refresh disclosure
- **THEN** every field the disclosure carries today is still present
- **AND** no caller has to change to keep reading it
