## MODIFIED Requirements

### Requirement: The CLI has one primary entry and flat command tree

The formal CLI SHALL use `unity-puer-exec` as its single primary entry. The authoritative flat command tree SHALL include `wait-for-log-pattern`, `wait-for-exec`, `wait-for-result-marker`, `wait-for-compile`, `get-log-source`, `get-log-briefs`, `exec`, `play`, `pause`, `stop`, `ensure-closed`, `resolve-blocker`, `get-blocker-state`, `get-compile-errors`, and `get-compile-warnings`. The tree SHALL also accept `ensure-stopped` as a deprecated alias of `ensure-closed`.

This tree SHALL be the single declaration of the CLI's command set. The invocable command surface, the per-command help tiers, the top-level command summary, and runtime guidance coverage SHALL all be defined over exactly this set, so a command cannot be invocable while being absent from help or guidance. A deprecated alias SHALL answer the same help tiers as the command it aliases, and SHALL be marked deprecated wherever it appears.

When distributed as a binary, the entry SHALL be `unity-puer-exec.exe` on Windows. The executable name (without extension) SHALL match the package name style. Agents and callers SHALL discover the binary by searching for `unity-puer-exec.exe` within the consuming Unity project's package cache, at the path `<PackageCache>/com.txcombo.unity-puer-exec@<version>/CLI~/unity-puer-exec.exe`.

#### Scenario: Agent discovers the CLI surface

- **WHEN** repository docs or help describe the CLI
- **THEN** `unity-puer-exec` is presented as the primary entry
- **AND** transitional aliases such as `unity-puer-session` are described only as compatibility paths, not as the authoritative surface
- **AND** transitional aliases remain thin adapters over the formal command behavior rather than separate feature-bearing command trees

#### Scenario: Agent discovers the binary CLI in a Unity project

- **WHEN** an agent needs to invoke the CLI within a Unity project that has the package installed via OpenUPM
- **THEN** the agent searches for `unity-puer-exec.exe` within the project directory
- **AND** the binary is located under `Library/PackageCache/com.txcombo.unity-puer-exec@<version>/CLI~/`
- **AND** the binary provides the same command surface as the Python source entry

#### Scenario: Invocable set and documented set agree

- **WHEN** the set of commands the CLI accepts is compared with the set that answers help tiers, the set summarized in top-level help, and the set covered by runtime guidance
- **THEN** all four sets are the same set
- **AND** no command is invocable while absent from any of them

#### Scenario: Agent invokes the deprecated ensure-stopped alias

- **WHEN** an agent runs `ensure-stopped` with arguments valid for `ensure-closed`
- **THEN** the command behaves exactly as `ensure-closed`, with the same result statuses and exit codes
- **AND** the response identifies `ensure-stopped` as deprecated and names `ensure-closed`

#### Scenario: Top-level help separates play mode from closing the Editor

- **WHEN** an agent reads top-level help
- **THEN** `play`, `pause`, and `stop` are listed as play-mode commands
- **AND** `ensure-closed` is described as closing the Editor process, distinct from `stop`

### Requirement: Observation and stop commands keep their boundary

`wait-for-log-pattern` and `get-log-source` SHALL remain observation commands. `ensure-closed` SHALL remain the stopped-state command for the Editor process. Observation commands MUST NOT imply Unity launch ownership, and `ensure-closed` in base-url mode MUST NOT kill the target. The play-mode `stop` command SHALL NOT close the Editor process.

In project mode, `ensure-closed` SHALL decide whether the project is stopped from project-local state — the project's Unity lockfile and the Editor's published endpoint — rather than from a process id recorded earlier or from a machine-wide count of Unity processes. A stop action SHALL target only a process the published endpoint identifies as belonging to the target project. Process-liveness detection SHALL be independent of the host operating system's display language.

#### Scenario: Agent checks observable log source

- **WHEN** `get-log-source` succeeds
- **THEN** the result reports `result.status = "log_source_available"`
- **AND** the payload includes stable `result.source`

#### Scenario: Agent ensures a base-url target is stopped

- **WHEN** `ensure-closed --base-url ...` is invoked
- **THEN** the command may inspect state only
- **AND** it does not perform kill behavior against that direct-service target

#### Scenario: Project with no running Editor is reported stopped

- **WHEN** `ensure-closed` (project mode) runs and the project's Unity lockfile is not held
- **THEN** the command reports the target as `stopped`
- **AND** it reports so regardless of how many unrelated Unity Editor processes are running on the machine

#### Scenario: A live Editor is not reported stopped

- **WHEN** `ensure-closed` (project mode) runs and the project's Unity lockfile is held
- **THEN** the command does not report the target as `stopped`
- **AND** it reports so regardless of whether any earlier session record named a process that has since exited

#### Scenario: A stop action never targets another project

- **WHEN** `ensure-closed` performs a kill in project mode
- **THEN** the process it targets is the one the target project's published endpoint identifies
- **AND** no process belonging to a different project is targeted

#### Scenario: Stopped detection does not depend on OS display language

- **WHEN** `ensure-closed` (project-path mode) evaluates process liveness on a non-English Windows host
- **THEN** the reported result reflects actual process state
- **AND** it is not altered by a localized process-listing message

#### Scenario: Play-mode stop leaves the Editor running

- **WHEN** an agent runs `stop`
- **THEN** the Editor process keeps running in edit mode

### Requirement: Help states that PlayMode transitions are asynchronous requests

Help SHALL present `play`, `pause`, and `stop` as the normal way to change the Editor play state, and SHALL state that they return after the transition completes. For scripts that set the play state directly through `exec`, help SHALL still state that this issues a request rather than completing a transition, and that a successful `exec` response does not establish that the transition finished. Help SHALL state that application-layer readiness is separate from the play state in both cases. It SHALL present the generic sequence: change the play state, then wait for the readiness signal the task requires.

#### Scenario: Agent switches PlayMode before acting

- **WHEN** an agent reads help before changing the Editor play state
- **THEN** help presents `play` / `pause` / `stop` as the normal path
- **AND** help states that application-layer systems may not be ready even after the play state has changed
- **AND** help presents the change-state-then-wait-for-readiness sequence

#### Scenario: Agent sets PlayMode from a script

- **WHEN** an agent reads help before setting the Editor play state from an `exec` script
- **THEN** help states that a successful `exec` response means the transition was requested, not completed
- **AND** help points to the play-mode commands as the completing alternative
