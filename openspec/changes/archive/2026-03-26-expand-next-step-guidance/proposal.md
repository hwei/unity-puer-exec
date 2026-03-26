## Why

The current CLI runtime only emits a `next_step` continuation hint on `exec → running`, always pointing to `wait-for-exec`. In practice, an AI agent faces many other response states across all ten commands where the reasonable next action is non-obvious—`modal_blocked`, `unity_stalled`, `missing`, `no_blocker`, etc. Agents must recall help documentation to decide what to do, creating a gap between what the runtime tells them and what the help system taught them. Expanding the guidance surface directly in runtime responses reduces agent decision latency and removes the need to memorize the full command tree before operating effectively.

## What Changes

- **BREAKING**: Replace the single-valued `next_step` field with a plural `next_steps` array of action candidates, each carrying `command`, optional `argv`, and a `when` hint describing when the action is appropriate.
- Add a `situation` string field for response states where there is no concrete next command but the agent benefits from understanding the current predicament (e.g., `not_available`, `no_supported_blocker`).
- Extend guidance coverage to all commands and all response statuses that have a non-trivial follow-up or situational explanation.
- Add a global `--suppress-guidance` flag (before the command name) that omits both `next_steps` and `situation` from responses, for proficient agents that do not need runtime hints.
- Expand `--help-status` output to include situation-level explanations for each status, so agents using `--suppress-guidance` can still query status meanings on demand.

## Capabilities

### New Capabilities
- `runtime-guidance`: Defines the contract for multi-candidate `next_steps`, `situation` fields, the `--suppress-guidance` global flag, and the per-command × per-status guidance matrix.

### Modified Capabilities
- `formal-cli-contract`: The existing "continuation hint" requirement (single `next_step` pointing to `wait-for-exec`) is replaced by the broader `runtime-guidance` contract. `--help-status` output requirements expand to include situation descriptions.

## Impact

- `cli/python/unity_puer_exec_runtime.py`: Replace `_next_step_payload` with a matrix-driven guidance builder; emit `next_steps` and `situation` on all command response paths.
- `cli/python/unity_puer_exec_surface.py`: Add `--suppress-guidance` to the top-level parser.
- `cli/python/help_surface.py`: Expand `--help-status` rendering to include situation explanations; add `--suppress-guidance` to discoverable help text.
- `openspec/specs/formal-cli-contract/spec.md`: Update continuation-hint requirement and help-status scenarios.
- All existing callers and tests that read `next_step` (singular) must migrate to `next_steps` (plural array).
