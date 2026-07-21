# Response File Output

## Purpose

Define the `--response-file` global formal option: how large or fully-detailed command responses are persisted to an explicit file as the complete normalized JSON envelope, how a compact verifiable reference is emitted on the normal output stream in their place, and the atomicity and failure-reporting guarantees that keep this path safe to rely on.
## Requirements
### Requirement: Formal command responses can be persisted to an explicit file

The formal CLI SHALL accept a global `--response-file <path>` option for commands that produce machine-readable JSON. When supplied, the CLI SHALL persist the complete normalized JSON response envelope that would otherwise be emitted by the command, after command-specific response enrichment and before response-file projection.

#### Scenario: Completed exec response is written to a file

- **WHEN** a caller invokes `exec --response-file X:/work/.tmp/exec-response.json` and the script completes with a JSON-serializable result
- **THEN** the file contains the complete completed exec response including the script `result`, request identity, log range, brief sequence, and any applicable guidance
- **AND** the stored response is not reduced to only the script-authored result value

#### Scenario: Retained result is recovered through wait-for-exec

- **WHEN** an exec request has already completed with a large result
- **AND** the caller invokes `wait-for-exec --request-id R --response-file X:/work/.tmp/recovered.json`
- **THEN** the retained terminal response for `R` is written without executing the script again

#### Scenario: Full-text briefs compose with response-file output

- **WHEN** a caller invokes `get-log-briefs --full-text --include 3 --response-file X:/work/.tmp/brief.json` for a large log entry
- **THEN** the complete get-log-briefs response, including the selected brief's full text, is written to the requested file

### Requirement: Response-file projection returns a compact verifiable reference

After a response file is written successfully, the CLI SHALL emit a compact JSON reference on the same output stream that would have carried the unprojected response. The reference SHALL preserve each available routing field among `ok`, `status`, `operation`, `request_id`, `phase`, and `session_marker`, and SHALL include `response_file.path`, `response_file.encoding`, `response_file.byte_count`, and `response_file.sha256`. The path SHALL be absolute, the encoding SHALL be `utf-8`, and the size and SHA-256 SHALL describe the exact stored bytes.

#### Scenario: Large successful response produces a bounded stdout reference

- **WHEN** a successful command uses `--response-file` and its unprojected response is larger than the caller's normal output budget
- **THEN** stdout contains the compact response-file reference instead of the complete inline result
- **AND** `response_file.byte_count` and `response_file.sha256` verify the stored response
- **AND** the command retains the underlying success exit code

#### Scenario: Structured stderr response preserves stream and exit semantics

- **WHEN** a formal command would emit a structured JSON failure response on stderr
- **AND** response-file persistence succeeds
- **THEN** the compact reference is emitted on stderr
- **AND** the underlying command exit code is unchanged

### Requirement: Response-file persistence is atomic

The CLI SHALL write the response through a temporary sibling of the destination and atomically replace the destination only after the complete response bytes have been written and closed. It SHALL create missing parent directories. If the destination already exists, successful completion SHALL replace it as one complete file rather than exposing a partial intermediate state.

#### Scenario: Existing response file is replaced completely

- **WHEN** a caller targets an existing response file
- **THEN** readers observe either the complete previous file or the complete new response
- **AND** they do not observe a partially written JSON document

#### Scenario: Parent directory does not exist

- **WHEN** the parent directory of an otherwise valid response-file path is absent
- **THEN** the CLI creates the required directories and persists the response

### Requirement: Persistence failure does not misreport execution outcome

If response-file persistence fails, the CLI SHALL NOT emit a successful response-file reference. It SHALL emit the original unprojected command response on its normal stream with an additive `response_file_error`, preserve the underlying command exit code and request identity, and leave any pre-existing destination unchanged when atomic replacement did not complete.

#### Scenario: File write fails after exec completed

- **WHEN** an exec request completes but the requested response file cannot be written or replaced
- **THEN** the response continues to report the exec request's completed status and request identity
- **AND** it includes `response_file_error`
- **AND** it does not claim that the requested file contains the result

### Requirement: Default command output remains inline

When `--response-file` is absent, formal commands SHALL retain their existing response stream, JSON shape, and exit-code behavior. The first version SHALL NOT automatically spill large responses based on an implicit size threshold.

#### Scenario: Caller does not request response-file output

- **WHEN** a caller invokes a formal command without `--response-file`
- **THEN** the complete response is emitted inline exactly as required by the command's existing contract
- **AND** no response artifact is created automatically
