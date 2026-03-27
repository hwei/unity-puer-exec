## Why

Long observation responses can emit very large repeated `brief_sequence` strings, which makes machine-readable output noisy and harder for humans and agents to scan. The recent OpenUPM real-host experiment made that cost visible during import-heavy runs.

## What Changes

- Compress repeated observation-sequence runs into a compact, deterministic textual encoding instead of expanding every repeated character literally.
- Apply the compact encoding consistently anywhere the CLI emits `brief_sequence`.
- Keep the sequence machine-usable while making long import-heavy responses easier to read.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `log-brief`: the `brief_sequence` contract changes from one-character-per-brief expansion to a compact run encoding.
- `formal-cli-contract`: async observation guidance continues to rely on `brief_sequence`, but now references the compact encoded form.

## Impact

- Log observation response formatting
- Any tests or docs that currently assume fully expanded `brief_sequence`
- [`openspec/specs/log-brief/spec.md`](F:/C3/unity-puer-exec-workspace/unity-puer-exec/openspec/specs/log-brief/spec.md)
- [`openspec/specs/formal-cli-contract/spec.md`](F:/C3/unity-puer-exec-workspace/unity-puer-exec/openspec/specs/formal-cli-contract/spec.md)
