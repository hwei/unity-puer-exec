# Proposal

## Why

`_invoke_reset_jsenv` in `cli/python/unity_puer_exec_runtime.py` (currently line 1411) is
dead code. It is the only one of the seven `invoke_command` call sites audited by
`2026-10-13-classify-peer-reset-on-all-transport-callers` that serves no command: it has no
caller anywhere in the repository, and no `reset-jsenv` command exists in the parser
(`exec` carries the JsEnv reset as the `--reset-jsenv-before-exec` flag instead). The audit had
to record "command path: none" for it, which is a symptom worth removing rather than carrying.

## What Changes

- Remove the unused `_invoke_reset_jsenv` function.
- Confirm no caller, test, or documentation depends on it (nothing does today).
- Keep `--reset-jsenv-before-exec` and the `reset_jsenv_before_exec` payload field untouched;
  the in-exec reset path is unaffected.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

(none)

No spec-level behavior changes: this removes an unreachable private helper. The externally
observable CLI surface, payloads, and exit codes are unchanged, so `.openspec.yaml` sets
`skip_specs: true` and no delta spec is written.

## Impact

- Affected code: `cli/python/unity_puer_exec_runtime.py` only.
- Affected validation: the command-layer peer-reset coverage stays green; no new test is
  required for the removal itself.
- Inherited context: follow-up candidate from
  `openspec/changes/archive/2026-10-13-classify-peer-reset-on-all-transport-callers/design.md`.
