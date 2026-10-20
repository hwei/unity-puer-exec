# Proposal

## Why

Agents that drive `unity-puer-exec` hit bugs and friction that never reach the maintainer, because nothing in the CLI surface tells them that feedback is wanted or where it goes. User agents learn the tool through `--help` and runtime responses rather than this repository, so that is where the invitation has to live — disclosed progressively, so it costs almost nothing until something actually goes wrong.

## What Changes

- Add a one-line `Feedback` pointer to top-level `--help` that names `unity-puer-exec --help-feedback` and nothing more.
- Add a new global help topic `unity-puer-exec --help-feedback` that carries the full reporting procedure: ask the user and file only after confirmation, redact project-private content (the repository is public), search existing issues before filing, what to include (`--version`, command line, status/exit code, expected vs actual, minimal repro), and a prefilled `issues/new` URL fallback when `gh` is unavailable. It covers both bugs and workflow friction.
- Add a CLI-owned envelope field `failure_origin` to responses whose cause is very likely a defect in the tool itself, with exactly two trigger values:
  - `cli_internal`: the CLI's catch-all handler caught an uncaught exception (`status: "failed"`, exit 1).
  - `service_internal`: the Unity control service answered HTTP 500 with its own unhandled-request `internal_error` body. Today the CLI reports this as `not_available` with `http_status: 500` and discards the body; that status and exit code stay, only the field is added.
- When `failure_origin` is present, compose a feedback hint into `situation` and add a `next_steps` candidate pointing at `--help-feedback`. No other status receives the hint — script errors, usage errors, transport/environment states (`not_available`, `empty_response`, launch/readiness failures, modal blockers, compile errors, version mismatch, `refresh_unsettled`) are explicitly excluded.
- Add GitHub Issue Forms (bug, friction) so agent-filed reports arrive with consistent fields.
- Add one sentence to the README Usage section (and its zh-CN translation) mentioning `--help-feedback`.

No status values or exit codes change; `failure_origin` is additive.

## Capabilities

### New Capabilities
- `agent-issue-feedback`: how the CLI invites and guides agents to report defects and friction upstream — the top-level pointer, the `--help-feedback` topic, the `failure_origin` classification, and the trigger-limited runtime hint.

### Modified Capabilities
<!-- none: the hint composes on a CLI-owned envelope field, following the existing compile_blocked composition precedent in runtime-guidance, without changing its requirements -->

## Impact

- `cli/python/help_surface.py`: top-level `Feedback` section, `--help-feedback` renderer, feedback hint/candidate composition.
- `cli/python/unity_puer_exec_surface.py`: `--help-feedback` handling beside `--help-example`.
- `cli/python/unity_puer_exec_runtime.py`: set `failure_origin` in the catch-all handler and when a service `internal_error` is surfaced; compose guidance in `_attach_guidance`.
- `cli/python/direct_exec_client.py`: possibly, if the service 500 body is not preserved through to the payload today.
- `.github/ISSUE_TEMPLATE/`: new issue forms.
- `README.md`, `README.zh-CN.md`: one Usage sentence each.
- Tests in `tests/` for help rendering, trigger classification, and non-trigger exclusion.
