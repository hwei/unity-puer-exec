# Design

## Scope

This change implements the accepted async redesign and removes the older continuation-token model instead of running both in parallel.

In scope:

- CLI command tree updates
- CLI response-shape updates
- package/server endpoint and async-state updates
- help and example updates
- regression and contract tests

Out of scope:

- preserving `get-result` for migration compatibility
- redesigning diagnostics visibility beyond the already accepted note that diagnostics may later become opt-in by default

## Target Workflow

The formal long-running workflow becomes:

1. Caller runs `exec --include-log-offset`
2. Script synchronously returns a `correlation_id`
3. `exec` returns top-level `log_offset`
4. Script later emits a single-line JSON marker with the fixed product prefix
5. Caller runs `wait-for-result-marker --correlation-id ... --start-offset ...`

Representative marker:

```text
[UnityPuerExecResult] {"correlation_id":"12ab...","payload":"..."}
```

## CLI Surface Changes

### Remove `get-result`

Remove `get-result` from:

- command parser
- help surface
- formal command reference
- tests that describe the formal command tree

### Extend `wait-for-log-pattern`

Retain `wait-for-log-pattern` as the regex primitive and add:

- `--extract-group N`
- `--extract-json-group N`

Rules:

- the two extraction modes are mutually exclusive
- `--extract-group N` returns group text
- `--extract-json-group N` parses group `N` as JSON and returns the parsed object
- callers that want the full match may use `--extract-group 0`

### Add `wait-for-result-marker`

Add a high-level alias or command entry named `wait-for-result-marker`.

Inputs:

- `--project-path` or `--base-url`
- `--correlation-id`
- `--start-offset`
- optional `--expected-session-marker`
- normal timeout and readiness parameters already used by observation commands

Matching rules:

- fixed marker prefix owned by the product
- parse the JSON body from the standard marker regex
- ignore invalid-JSON marker candidates
- ignore markers whose `correlation_id` does not match
- continue waiting until a valid matching marker is found or normal wait termination occurs

Representative success shape:

```json
{
  "ok": true,
  "status": "completed",
  "operation": "wait-for-result-marker",
  "session": {
    "...": "..."
  },
  "result": {
    "status": "result_marker_matched",
    "marker": {
      "correlation_id": "12ab...",
      "...": "..."
    },
    "diagnostics": {
      "matched_log_text": "[UnityPuerExecResult] {...}",
      "matched_log_pattern": "^\\[UnityPuerExecResult\\] (.+)$"
    }
  }
}
```

## `exec` Changes

`exec` gains `--include-log-offset`.

Rules:

- when requested, `exec` returns top-level `log_offset`
- `log_offset` is observation metadata, not script semantic result
- `log_offset` is returned consistently for both `completed` and `running` responses
- `exec` does not infer whether the script intends a result-marker workflow; callers opt in explicitly

Representative shape:

```json
{
  "ok": true,
  "status": "completed",
  "operation": "exec",
  "log_offset": 12345,
  "result": {
    "correlation_id": "12ab..."
  }
}
```

## Package / Server Changes

Remove continuation-based job result retrieval from the package-owned server path:

- remove `/get-result`
- remove or simplify the job table and continuation-token-specific lookup logic
- keep only the async state needed for current execution, logging, and observation support

This change should prefer deleting continuation-specific code rather than wrapping it in dead compatibility layers.

## Help And Examples

Update help so the recommended async flow is discoverable from the CLI alone:

- `exec --include-log-offset`
- `wait-for-result-marker --correlation-id ... --start-offset ...`
- low-level `wait-for-log-pattern` extraction examples

Add at least one example script that:

- generates a `correlation_id`
- returns it synchronously from `exec`
- later emits the terminal result marker

## Testing

Add or update tests covering:

- command tree no longer includes `get-result`
- `exec --include-log-offset` on both synchronous completion and running cases
- `wait-for-log-pattern --extract-group`
- `wait-for-log-pattern --extract-json-group`
- mutual exclusion of the two extraction modes
- `wait-for-result-marker` successful match
- invalid JSON marker candidate ignored
- wrong `correlation_id` marker ignored
- optional `--expected-session-marker` same-session failure path

## Follow-Up Intentionally Deferred

This change does not redesign diagnostics visibility. `wait-for-result-marker` may still return lightweight diagnostics by default. If the repository later wants diagnostics hidden by default, that should be a separate change.
