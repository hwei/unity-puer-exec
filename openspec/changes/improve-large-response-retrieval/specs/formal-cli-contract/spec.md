## ADDED Requirements

### Requirement: Help distinguishes structured results from diagnostic logging

The formal CLI help surface SHALL state that immediate JSON-serializable data intended for machine consumption is returned from the default-exported exec function and appears in top-level `result`. It SHALL direct callers expecting a large response to `--response-file`. It SHALL describe `console.log` and result markers as diagnostic or asynchronous observation paths rather than the preferred transport for a large synchronous result.

#### Scenario: Agent plans a large synchronous inspection result

- **WHEN** an agent reads `exec --help` before authoring a script that produces a large JSON object
- **THEN** the help directs the script to return the object from its default-exported function
- **AND** the help identifies `--response-file` as the way to avoid inline output truncation
- **AND** the agent is not instructed to move the synchronous object through Editor.log

### Requirement: Response-file output is discoverable as a global formal option

Top-level help and relevant per-command help SHALL document `--response-file <path>`, its compact reference response, and the fact that the stored file contains the complete normalized command envelope. Help for `wait-for-exec` SHALL explain that the option can recover an already-completed large result by the same `request_id`.

#### Scenario: Agent recovers an unexpectedly large result

- **WHEN** an agent has an accepted or completed exec `request_id` whose inline result could not be fully inspected
- **THEN** `wait-for-exec --help` exposes a copyable recovery path using the same `request_id` and `--response-file`
- **AND** the guidance does not recommend re-executing the script with a fresh request identity

### Requirement: Execution lifecycle logs do not echo complete result payloads

The Unity execution service SHALL keep successful completion lifecycle logging bounded independently of result size. The completion log SHALL include the request identity and result UTF-8 byte count, but SHALL NOT include the serialized result, a result preview, or script-returned field values. The complete result SHALL remain available through the exec job response.

#### Scenario: Script returns a large or sensitive object

- **WHEN** an exec script completes with a large JSON-serializable result
- **THEN** Editor.log contains a bounded completion lifecycle entry with the request identity and result byte count
- **AND** Editor.log does not contain the complete result or a preview emitted by the execution service
- **AND** `exec` or `wait-for-exec` still returns the authoritative result
