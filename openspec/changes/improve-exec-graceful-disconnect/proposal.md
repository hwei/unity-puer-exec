## Why

The OpenUPM real-host validation showed that a request can complete successfully after an earlier client-side timeout or interrupted wait, but Unity-side logs still emit noisy transport exceptions such as `Unable to write data to the transport connection`. The behavior looks recoverable, but the current disconnect path is not graceful.

## What Changes

- Define a more graceful server/client disconnect behavior for accepted exec requests whose original caller is no longer waiting on the first transport response.
- Reduce misleading transport exception noise when a request remains recoverable and later completes successfully.
- Preserve the current recovery contract based on `request_id` rather than replacing it.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `formal-cli-contract`: accepted request lifecycle rules expand to describe graceful handling when the original client connection ends before Unity-side work has fully drained.

## Impact

- CLI transport/request lifecycle handling
- Unity-side request response path
- [`openspec/specs/formal-cli-contract/spec.md`](F:/C3/unity-puer-exec-workspace/unity-puer-exec/openspec/specs/formal-cli-contract/spec.md)
