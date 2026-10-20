# Design

## Context

- User agents discover the CLI through top-level `--help`, per-command help tiers, `--help-example`, and the `next_steps` / `situation` guidance on responses. The README only tells them to start from `--help`. Feedback guidance has to live in that surface to be seen at all.
- `runtime-guidance` requires candidate selection to depend on command and status only, and never on script-authored `result`. It already allows guidance to be composed on CLI-owned envelope fields: `compile_blocked` adds play-mode exit candidates on top of the matrix selection.
- `status: "failed"` is overloaded. Script exceptions, invalid regexes, bad log ranges, and genuinely uncaught CLI exceptions all produce it. Keying the hint on `failed` would make agents offer issue reports for their own script bugs.
- The CLI catch-all is the `except Exception` handler in `unity_puer_exec_runtime.py` (around line 628), which builds `unexpected_failure_payload` and exits 1.
- The Unity service catch-all (`UnityPuerExecServer.cs`, request handler) logs the exception and answers HTTP 500 with `{"ok":false,"status":"failed","error":"internal_error"}`. On the CLI side, `direct_exec_client.invoke_command` maps every `HTTPError` to `status: "not_available"` with `http_status`, and discards the body.

## Goals / Non-Goals

**Goals:**
- Progressive disclosure: one line in top-level help, the full procedure behind `--help-feedback`, structured fields in the GitHub issue forms.
- A runtime hint only where a tool defect is the most likely explanation.
- No change to existing statuses, exit codes, or matrix-selected candidates.

**Non-Goals:**
- A CLI subcommand that files issues itself. Auth, redaction, and the user-confirmation gate stay with the calling agent.
- Telemetry or automatic reporting of any kind.
- Reclassifying the HTTP 500 path into a new status, and cleaning up the overloaded `failed` status. Both are out of scope here.

## Decisions

1. **Dedicated `--help-feedback` global flag rather than a `--help-example` entry.** Help examples are Unity workflow recipes and are listed together under "Common Help Examples". Feedback is a separate concern, and listing it there would add noise to every top-level help read. It is handled in `unity_puer_exec_surface.handle_top_level_help` next to `--help-example`, before parser construction, the same way `--version` and `--help-example` are, so it never touches a selector or Unity.

2. **Top-level pointer is exactly one bullet.** This keeps the per-read token cost low for the common case where nothing is wrong. The procedure text lives in a renderer in `help_surface.py`.

3. **A `failure_origin` envelope field, not a new status.** Adding a status would change values that agents and tests already branch on. A CLI-owned field follows the `compile_blocked` precedent: matrix selection stays keyed on (command, status), and the feedback candidate is appended on top. The field is also emitted under `--suppress-guidance`, so programmatic callers can still detect the condition.

4. **Trigger set limited to two origins.**
   - `cli_internal`: set only in the CLI's unclassified-exception handler. Any exception that reaches it escaped every specific handler by definition, which is the strongest available signal of a CLI defect.
   - `service_internal`: set when `HTTPError.code == 500` and the body parses as JSON with `error == "internal_error"`. That body is written only by the service's own request-handler catch, so it means the C# service threw. The CLI reads the body inside the existing `HTTPError` branch and keeps `status: "not_available"`, `http_status`, and `EXIT_NOT_AVAILABLE` unchanged.
   - Excluded on purpose, because they usually have environmental or user-side causes: script `failed`, usage statuses, `not_available` from other causes, `empty_response`, launch and readiness failures, modal blockers, compile errors, version mismatch, and `refresh_unsettled`. These can be added later if evidence shows they are mostly defects.

5. **Where composition happens.** `_attach_guidance` already receives the payload. Once the matrix candidates are built, it appends the feedback candidate (`argv: ["unity-puer-exec", "--help-feedback"]`, `command` set to the invoked command, following the `--help-args` candidate precedent) and the situation sentence when `payload.get("failure_origin")` is set. Payload paths that never call `_attach_guidance` with the payload (for example, direct-client passthrough on `not_available`) have to be checked during apply, so that the service case actually reaches composition.

6. **Issue forms.** Add `.github/ISSUE_TEMPLATE/bug.yml` and `friction.yml`, with a `config.yml` that keeps blank issues enabled. The forms ask for the same fields that `--help-feedback` lists, so an agent can fill them from that topic. The forms are repository governance, not product CLI behavior, so they get no spec requirement.

## Risks / Trade-offs

- **The procedure text is unenforceable guidance.** Agents may skip the confirmation gate or the redaction rules. Mitigation: state both as the first two steps in imperative form. Nothing more can be enforced from the CLI side.
- **The service 500 body may be unread today.** Reading it means a small change to the `HTTPError` branch, and a body read on a broken connection could itself raise. Wrap the read so any failure falls back to the current payload without the field.
- **False negatives.** Some real defects show up as `failed` script errors or `not_available` and will get no hint. That is accepted: the user asked for high-confidence triggers only, and the one-line top-level pointer still covers friction the agent notices on its own.
- **Help text drift.** The repository URL is hard-coded in help text. Keep it in a single constant so tests and both renderers share it.
