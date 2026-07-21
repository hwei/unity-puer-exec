## Context

`unity-puer-exec` already transports an immediate JSON-serializable script return as the top-level `result`, and the Python transport reads the complete HTTP body. The practical loss occurs one layer later: agent shell tools commonly cap captured stdout, so a valid response can be truncated before the agent can inspect it. Replaying `wait-for-exec` without changing the output destination returns the same oversized payload and does not solve that boundary.

Log observation has a related but distinct shape. `get-log-briefs` intentionally returns a 100-character first-line preview and byte offsets. A caller that needs one complete entry must currently leave the CLI surface, resolve Editor.log, and implement its own byte seek. In addition, `UnityPuerExecServer.CompleteJob` writes the complete serialized script result into Editor.log, duplicating large or sensitive structured data into the diagnostic channel.

This change follows the repository's existing CLI-native principle: the full response remains machine-readable and recoverable through the formal CLI, while compact output stays the default. These product contracts belong in durable specs; repository context and external validation-host setup remain governed by `openspec/config.yaml` and `validation-host-integration` rather than being copied into the product requirements.

## Goals / Non-Goals

**Goals:**

- Provide a deterministic caller-selected file sink for complete formal-command responses.
- Keep the normal stdout/stderr payload compact when file output is requested while preserving status, exit-code, and stream semantics.
- Allow an already-completed large `exec` result to be recovered through `wait-for-exec --response-file` without re-executing the script.
- Retrieve the complete text of explicitly selected log briefs without manual Editor.log reads.
- Keep Unity lifecycle logging bounded independently of script result size.
- Preserve the existing default response and brief shapes when callers do not opt in.

**Non-Goals:**

- Automatically spilling responses above an implicit size threshold.
- Managing temporary-file retention or choosing an output path on the caller's behalf.
- Adding a new arbitrary raw-log-range command.
- Changing Promise/thenable result handling or the result-marker workflow.
- Renaming or otherwise redesigning the existing `get-log-briefs --include` selector.
- Addressing module-cache staleness, PuerTS bridge examples, or other feedback from the originating session.

## Decisions

### 1. `--response-file` is a global, explicit output projection

Every formal command accepts `--response-file <path>`. After normal command execution, response normalization, diagnostics, log-range enrichment, and guidance attachment are complete, the CLI writes the exact authoritative JSON envelope that it otherwise would have emitted. The same projection is applied whether that JSON would normally be written to stdout or stderr.

The option is explicit rather than an automatic size-triggered spill. Explicit output keeps existing parsers stable, avoids hidden temporary-file lifecycle policy, and lets agents select a workspace-local path such as `.tmp/result.json`. Help for the primary large-response workflows makes the option discoverable. If an agent did not predict the size of an `exec` result, it can recover the retained terminal response using the same `request_id` through `wait-for-exec --response-file`.

**Alternative considered:** add `--result-file` only to `exec`. Rejected because it loses the surrounding status, request identity, guidance, and log metadata and does not compose with `get-log-briefs` or future large formal responses.

**Alternative considered:** automatically spill above a fixed threshold. Deferred because tool output budgets differ, automatic omission of inline `result` changes the default contract, and an implicit temp location creates cleanup and provenance questions.

### 2. The file contains the pre-projection response; the console receives a compact reference

The response file contains the exact UTF-8 bytes of the normalized JSON string before response-file projection. No `response_file` self-reference is inserted into the file.

On the stream where the full JSON would normally appear, the CLI emits a compact JSON envelope that mirrors available routing fields (`ok`, `status`, `operation`, `request_id`, `phase`, and `session_marker`) and adds:

```json
{
  "response_file": {
    "path": "X:/work/.tmp/result.json",
    "encoding": "utf-8",
    "byte_count": 34812,
    "sha256": "..."
  }
}
```

The path is absolute. `byte_count` and `sha256` describe the exact stored bytes. The command's exit code and choice of stdout versus stderr remain those of the underlying command result, so output routing does not reinterpret execution success.

### 3. Persistence is atomic and failure falls back to the original response

The CLI creates missing parent directories, writes a sibling temporary file, flushes and closes it, and atomically replaces the requested destination. An existing destination is replaced only after the complete new response has been written. Temporary siblings are cleaned up best-effort.

If persistence or replacement fails, the destination is not reported as successful. The CLI emits the original unprojected response on its normal stream with an additive `response_file_error` description and preserves the underlying command exit code and request identity. This prioritizes recovery truth: a script that completed remains completed even if the optional local sink failed.

**Alternative considered:** replace the underlying command result with a new `response_file_write_failed` status. Rejected because file projection happens after Unity work and must not misrepresent a completed or recoverable exec request as though the execution itself failed.

### 4. Full log text is opt-in and requires explicit brief selection

`get-log-briefs --full-text` is valid only together with `--include`. Each selected brief keeps its existing `text` preview and gains `full_text`, containing the complete decoded raw byte span assigned to that brief. Unselected briefs are not returned merely because full-text mode is enabled, and the default shape remains unchanged.

The parser tracks line and entry boundaries from raw bytes so `start_offset` and `end_offset` delimit the exact stored span, including multibyte UTF-8 content. `full_text` decodes that span as UTF-8 using replacement for malformed sequences, matching the parser's existing tolerance. Callers expecting a large full-text entry can compose the command with `--response-file`.

Requiring explicit indices prevents an accidental request for full text of an entire compile or startup range. A separate raw-range command is unnecessary for the reported workflow because briefs already provide the selection and entry boundaries.

### 5. Unity completion logs record size, not result content

Successful job completion logs the request identity and UTF-8 result byte count, but not the serialized result or a preview. The authoritative value remains in the job snapshot and exec response. This keeps `brief_sequence` useful, avoids duplicating large payloads into Editor.log, and reduces accidental disclosure of returned project data.

### 6. Validation covers both protocol fidelity and real agent boundaries

Unit tests cover output projection, stream/exit preservation, atomic replacement, failure fallback, exact hashes, byte-accurate full-text spans, and unchanged defaults. Real-host validation returns a large Unicode object immediately, exercises a running request followed by `wait-for-exec --response-file`, retrieves a long selected log entry, and confirms the completion lifecycle line is bounded and does not contain the payload.

## Risks / Trade-offs

- **[Caller chooses a tracked or sensitive path]** → Help recommends `.tmp/`; the option remains explicit and reports an absolute path plus hash so the caller can verify the target.
- **[Atomic replace semantics vary by filesystem]** → Use a sibling temporary file and the platform's replace primitive; test Windows behavior because it is the primary environment.
- **[A file write fails after Unity side effects completed]** → Preserve the underlying status/request identity, emit the original response with `response_file_error`, and allow `wait-for-exec` recovery where applicable.
- **[Full-text parsing increases memory use]** → Require explicit brief indices and construct full text only for selected entries.
- **[Malformed UTF-8 cannot round-trip as text]** → Preserve exact byte offsets in metadata and use documented replacement decoding; Editor.log is expected to be UTF-8 text.
- **[Global option broadens test surface]** → Centralize projection after command normalization and add representative stdout, stderr, success, expected-state, and failure tests rather than duplicating command-specific writers.

## Migration Plan

1. Add the global parser/help surface and centralized response-file projection without changing default output.
2. Add full-text brief retrieval and byte-accurate span handling.
3. Bound Unity completion logging.
4. Run focused repository tests, help snapshots, package-layout checks, and external real-host regression.
5. Rollback is removal of the additive option/full-text field and restoration of the prior completion log line; no persisted product state or protocol migration is required.

## Open Questions

None required for apply. Automatic threshold-based spill may be reconsidered later using transcript evidence from the explicit response-file workflow.
