## ADDED Requirements

### Requirement: Help states the exec script environment boundary

Published exec script-authoring help SHALL state that an `exec` script runs in an execution environment separate from the host application's own JavaScript runtime environment, and that it therefore cannot reach that runtime's global variables, module-level state, or singletons. Help SHALL identify the shared C#/Unity object graph as the supported route from an `exec` script to a running application.

#### Scenario: Agent reads exec help before authoring a script

- **WHEN** an agent reads `unity-puer-exec exec --help` or `exec --help-args`
- **THEN** the help states that the script environment is separate from the host application's JavaScript runtime environment
- **AND** the help states that the application's globals, module state, and singletons are not reachable from the script
- **AND** the help identifies the shared C#/Unity object graph as the supported route to the running application

#### Scenario: Boundary is stated alongside the context contract

- **WHEN** help describes `ctx.globals` as same-service shared state
- **THEN** help also makes clear that this shared state is shared between `exec` requests, not shared with the host application's own JavaScript runtime

### Requirement: Help documents a cross-environment coordination pattern

Because the boundary alone tells a caller only what does not work, help SHALL describe the generic pattern that does: place or read state through shared C#/Unity objects that both sides can observe, and confirm the outcome through log-based observation. The pattern SHALL be described without depending on any particular UI framework or application architecture.

#### Scenario: Agent needs the running application to perform work

- **WHEN** an agent reads help while looking for a way to invoke the host application's own JavaScript functions
- **THEN** help describes shared-object coordination plus log observation as the supported approach
- **AND** help does not describe any mechanism for calling into the host application's JavaScript runtime directly

### Requirement: Help scopes framework-specific technique to project-local skills

Help SHALL state that application-framework-specific technique — UI widget-tree traversal, event invocation conventions, and application-specific operations — is outside the scope of this CLI's help and belongs in a project-local skill.

#### Scenario: Agent looks for UI-framework instructions in help

- **WHEN** an agent consults CLI help for how to locate and drive UI widgets in a specific UI framework
- **THEN** help states that such technique belongs in a project-local skill
- **AND** help does not contain framework-specific widget or event instructions

### Requirement: Help states that PlayMode transitions are asynchronous requests

Help SHALL state that setting the Unity Editor play state through `exec` issues a request rather than completing a transition, that the `exec` response returning successfully does not establish that the transition finished, and that application-layer readiness is a separate condition from the play state itself. Help SHALL present the generic sequence: request the transition, confirm the play state changed, then wait for the readiness signal the task requires.

#### Scenario: Agent switches PlayMode before acting

- **WHEN** an agent reads help before setting the Editor play state from a script
- **THEN** help states that a successful `exec` response means the transition was requested, not completed
- **AND** help states that application-layer systems may not be ready even after the play state has changed
- **AND** help presents the request, confirm, then wait-for-readiness sequence

### Requirement: Help distinguishes log range start from end by observation intent

Help SHALL state which end of a response `log_range` to use as `--start-offset` for each observation intent: `log_range.start` when waiting for output that the originating command itself produced, and `log_range.end` when observing activity that follows it.

#### Scenario: Agent chooses an observation checkpoint

- **WHEN** an agent reads help or a help example that passes a `log_range` value to `--start-offset`
- **THEN** help states that `log_range.start` applies when the awaited output came from the originating command
- **AND** help states that `log_range.end` applies when the awaited activity follows the originating command

### Requirement: Help states what the observation guards each protect against

Help SHALL state the distinct failure that `--start-offset` and `--expected-session-marker` each prevent: `--start-offset` prevents matching output produced before the intended observation window, and `--expected-session-marker` prevents accepting observation from a different Editor session. Help SHALL make clear that these address different failures rather than being alternatives.

#### Scenario: Agent configures a guarded observation

- **WHEN** an agent reads `wait-for-log-pattern --help-args` or a related help example
- **THEN** help states that `--start-offset` guards against stale output from before the intended window
- **AND** help states that `--expected-session-marker` guards against observing a different Editor session
- **AND** help indicates that the two guards cover different failures and are complementary

## MODIFIED Requirements

### Requirement: --code help warns about PowerShell $ expansion

The `--code` argument help text SHALL include a note that PowerShell users should use single quotes (`'...'`) when the code contains `$` characters (such as `$typeof`), or use `--file` as an alternative. The note SHALL also appear in `exec --help`, so a caller composing an inline `--code` value encounters it without first opening the argument help tier. The note SHALL state that shell expansion of `$` produces a JavaScript syntax error that does not name the shell as its cause.

#### Scenario: Agent reads --code help on PowerShell

- **WHEN** an agent reads `unity-puer-exec exec --help-args` on a Windows/PowerShell system
- **THEN** the argument help for `--code` mentions PowerShell single-quote usage for code containing `$`
- **AND** the help points to `--file` as the preferred alternative for multi-line or `$`-containing scripts

#### Scenario: Agent reads exec help before composing inline code

- **WHEN** an agent reads `unity-puer-exec exec --help`
- **THEN** the PowerShell single-quote note is present without requiring `--help-args`
- **AND** the note explains that shell expansion of `$` surfaces as a JavaScript syntax error rather than as a quoting error
