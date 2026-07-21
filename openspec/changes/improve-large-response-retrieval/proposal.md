## Why

Large JSON results and long Unity log entries currently exceed the practical output budget of agent shell tools. Although synchronous `exec` return values are carried intact in top-level `result`, callers have no CLI-native way to redirect the authoritative response to a durable file, and log briefs expose only a 100-character preview, forcing agents into manual Editor.log byte-range reads.

## What Changes

- Add an explicit response-file output mode for formal commands so callers can persist the complete final CLI response atomically and receive a compact, verifiable reference on the command's normal output stream; `exec`, `wait-for-exec`, and `get-log-briefs` are the primary large-response workflows.
- Keep immediate JSON-serializable script returns as the primary structured-result channel and make the help surface direct callers toward `return` plus response-file output instead of `console.log` for large synchronous data.
- Extend `get-log-briefs` with an opt-in full-text mode for explicitly selected brief indices while preserving the existing compact preview by default.
- Stop echoing complete script result payloads into Editor.log as execution lifecycle diagnostics; log bounded metadata instead.
- Add focused unit and real-host coverage for large Unicode responses, `exec`/`wait-for-exec` recovery, exact log-entry retrieval, and bounded lifecycle logging.

## Capabilities

### New Capabilities

- `response-file-output`: Defines explicit, atomic persistence of complete CLI response envelopes and the compact file-reference response returned to callers.

### Modified Capabilities

- `formal-cli-contract`: Adds the global response-file option to formal commands, clarifies the preferred large synchronous-result workflow, and prevents full result payloads from being duplicated into Unity lifecycle logs.
- `log-brief`: Adds opt-in retrieval of complete raw text for explicitly selected log briefs without changing the default 100-character preview contract.

## Impact

- **Python CLI:** command parsing, response normalization/output projection, atomic file persistence, hashing, help text, and recovery behavior.
- **Unity package:** execution-completion logging in `UnityPuerExecServer.cs` changes from full payload echoing to bounded metadata.
- **Tests:** CLI/unit coverage plus external validation-host regression coverage for large results and full-text log retrieval.
- **Compatibility:** default command output and default log-brief shapes remain unchanged when the new options are not supplied; no existing command or field is removed.
