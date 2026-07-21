## 1. Centralized Response-File Output

- [x] 1.1 Add global `--response-file <path>` parsing for formal commands and expose the option through top-level and per-command help without changing existing invocations.
- [x] 1.2 Implement a centralized post-normalization projection that atomically writes the exact unprojected JSON response, calculates UTF-8 byte count and SHA-256, and emits the compact absolute-path reference.
- [x] 1.3 Preserve the underlying exit code and stdout/stderr selection across projection, and implement write/replace failure fallback that emits the original response with `response_file_error` without corrupting an existing destination.
- [x] 1.4 Add `exec` and `wait-for-exec` guidance showing immediate `return` plus `--response-file`, including same-`request_id` recovery for an unexpectedly large completed result.

## 2. Selected Full-Text Log Retrieval

- [x] 2.1 Refactor log-brief span accounting to use exact raw byte boundaries for LF/CRLF and multibyte UTF-8 content while preserving existing grouping and preview behavior.
- [x] 2.2 Add `get-log-briefs --full-text`, require one or more explicit `--include` indices, and attach complete decoded `full_text` only to selected briefs.
- [x] 2.3 Document full-text selection, its bounded-use rule, and composition with `--response-file` in command help and guidance.

## 3. Bounded Unity Completion Logging

- [x] 3.1 Replace the full `resultJson` completion log in `UnityPuerExecServer` with request identity and UTF-8 result byte count while leaving the stored job result and HTTP response unchanged.
- [x] 3.2 Add package-level regression coverage proving completion logging contains neither full result content nor a preview of script-returned fields.

## 4. Repository Test Coverage

- [x] 4.1 Add CLI tests for successful response-file projection, exact stored envelope/hash/byte count, missing-parent creation, atomic replacement, and unchanged default inline output.
- [x] 4.2 Add representative tests for structured stdout and stderr responses, preserved exit codes/routing fields, and persistence-failure fallback with the previous destination left intact.
- [x] 4.3 Add log-brief tests for long selected entries, multiple indices, missing-`--include` rejection, exact CRLF spans, multibyte Unicode boundaries, and unchanged default brief shape.
- [x] 4.4 Update help and package-layout assertions for the new global option, large-result authoring guidance, full-text workflow, and bounded completion log contract.

## 5. Real-Host Validation Evidence

- [x] 5.1 Run a validation-host exec that returns a large Unicode JSON object through `--response-file` and verify the stored envelope, byte count, SHA-256, compact console reference, and absence of payload echo in Editor.log.
- [x] 5.2 Exercise an accepted request through `exec` followed by `wait-for-exec --response-file` with the same `request_id` and verify the script is not executed twice.
- [x] 5.3 Emit a long Unicode log entry, retrieve its selected brief with `--full-text --response-file`, and verify complete text plus exact byte offsets without manual Editor.log seeking.
- [x] 5.4 Record commands, observed payload metadata, hashes, and bounded-log findings under the change's `results/` directory.

## 6. Validation and Closeout

- [x] 6.1 Run the focused Python test suites for CLI runtime, direct exec, log briefs, package layout, and real-host integration instructions relevant to this change.
- [x] 6.2 Run `openspec validate improve-large-response-retrieval --strict --no-interactive`, inspect the final diff for scope and whitespace errors, and confirm all apply tasks and evidence are archive-ready.
- [x] 6.3 Complete the required apply closeout review and record either `No new follow-up work identified` or human-discussed follow-up candidates in an allowed category.
