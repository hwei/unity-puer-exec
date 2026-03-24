## Context

The current CLI already exposes `wait-for-log-pattern`, `--start-offset`, and `get-log-source`, but the latest help-only Prompt B rerun still left the intended CLI verification path after repeated `unity_stalled` outcomes. The gap is now narrower than general log discoverability: the product needs a clearer stalled-recovery path.

## Goals / Non-Goals

**Goals:**
- Make `unity_stalled` easier to recover from without guessing.
- Increase the chance that help-only agents keep final verification inside the CLI surface.
- Preserve the current ordinary log workflow rather than replacing it.

**Non-Goals:**
- Do not redesign the full log-observation subsystem.
- Do not broaden this change into unrelated compile-recovery or script-authoring issues.

## Decisions

### Decision: Start with the smallest stall-recovery improvement
The next session should first identify the narrowest change that makes a stalled `wait-for-log-pattern` result easier to continue correctly. That could be help-surface guidance, a better failure hint, a modest timeout or retry behavior adjustment, or a small combination.

### Decision: Judge the change against host-log fallback, not task success alone
Prompt B already succeeds. The acceptance question is whether the follow-up reduces the need for direct `Editor.log` inspection after `unity_stalled`.
