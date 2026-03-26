## Why

A help-only Prompt B discoverability probe (haiku subagent, 2026-03-25) showed that a weaker agent still assumed `ctx.getProjectRoot()` exists, despite the correct ctx contract and `derive-project-path-from-unity-api` example already being documented. The root cause is that the ctx contract is only visible in `exec --help-args` (the Script Context section), while `exec --help` (Quick Start) does not mention ctx limitations at all. An agent that only reads Quick Start has no reason to consult `--help-args` before writing its first script.

Upstream evidence: `add-log-brief-capability` task 4.3 evaluation, archived Prompt B transcript comparisons from `clarify-exec-script-context-contract`.

## What Changes

- Surface a brief ctx-contract warning in `exec --help` Quick Start so agents see the limitation before their first script attempt.
- Keep the full contract and derivation example in `--help-args` and `--help-example` where they already live.

## Capabilities

### Modified Capabilities
- `agent-cli-discoverability-validation`: Prompt B reruns can measure whether first-pass `ctx` field assumptions decrease after the help change.

## Impact

- Small, focused help-text change.
- No runtime or API changes.
- Directly addresses the last remaining ctx-discoverability gap observed in the haiku probe.
