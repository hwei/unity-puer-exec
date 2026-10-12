# Design

## Context

See `proposal.md` for the motivation. The relevant current state:

- `direct_exec_client.invoke_command` is the shared HTTP boundary. Since
  `diagnose-empty-response-parse-error` it returns a **parseable** JSON payload for an
  empty/unparseable body (`status: "empty_response"`) and for an unreachable target
  (`status: "not_available"`). Both are transport conditions, not command results.
- `_post_play_mode` loops on `direct_exec_client.invoke_command("play-mode", ...)`, then
  does `body = _parse_response_body(stdout_text, stderr_text); if body is not None: return`.
  Because the boundary now always returns parseable JSON, `body` is never `None` for a
  dropped endpoint, so the loop's re-resolve/retry branch (and its docstring promise) is
  unreachable.
- `_run_play_mode_command` maps every non-ok body to `return 1, ...`, discarding the
  status's formal exit code. The transport boundary's formal code for a dropped endpoint is
  `EXIT_NOT_AVAILABLE` (12); `modal_blocked` is 19.

`_play_pre_settle` (the `play` refresh gate) already treats `EXIT_NOT_AVAILABLE` as "the
endpoint is down for the reload" and polls to its deadline; only the `play-mode` POST and
the command envelope lose that distinction.

## Goals / Non-Goals

**Goals:**

- Absorb a dropped `play-mode` endpoint inside `_post_play_mode`'s existing re-resolve loop,
  instead of surfacing it as terminal.
- Preserve the formal exit code for a non-success `play` / `pause` / `stop` result.
- Keep the retry narrow: only transport conditions are retried; a server-answered failure
  is reported as-is.

**Non-Goals:**

- Changing the `exec` transport boundary (already fixed).
- Adding a new public command or option.
- Changing play-mode success payloads, transition semantics, or the `_play_pre_settle`
  compile gate.
- Retrying non-transport statuses such as `invalid_play_state`, `modal_blocked`, or
  `version_mismatch`.

## Decisions

### Decision 1: Retry in `_post_play_mode`, not in `_run_play_mode_command`

`_post_play_mode` already owns the bound and the re-resolution helper
(`_play_probe_endpoint`) and is documented to absorb the drop. Retrying at the command
level would re-run the pre-state probe and the refresh gate, which is both slower and
semantically wrong. Alternative — put the retry in a shared wrapper — adds indirection for
one caller; rejected.

### Decision 2: Retry only the transport family, keyed on status

The fix must not retry a real command failure. `_post_play_mode` inspects the parsed
`status` and retries only for `empty_response` and `not_available` (and, defensively, when
no body parses at all). Any other parseable body — including `invalid_play_state`,
`modal_blocked`, `version_mismatch`, and `http_status == 404` — is returned immediately.
Alternative — retry on `exit_code == EXIT_NOT_AVAILABLE` — is equivalent but couples the
retry to a numeric code; keying on the named status is clearer and survives a code change.

### Decision 3: Preserve the formal exit code via the client's single mapping

`_run_play_mode_command` currently returns a hard-coded `1` for any non-ok body. It should
reuse the boundary's status→exit-code mapping so `modal_blocked` → 19, `empty_response` /
`not_available` → 12, and so on, while keeping `invalid_play_state` and
`_play_mode_absent` (`http_status == 404`) as their existing special cases. The mapping
currently lives in `direct_exec_client._status_to_exit_code`; expose it as a public
`status_to_exit_code(payload)` and have the runtime call it. Alternative — duplicate the
map in the runtime — guarantees drift and is rejected. The already-fixed boundary payload
also carries an explicit `exit_code`; where present it stays authoritative.

### Decision 4: Reuse the command's existing `--timeout-seconds` budget

The retry deadline is the same bound the command already uses to reach the target state
(`time.monotonic() + timeout_seconds`), so a dropped endpoint cannot extend a command past
the budget the caller asked for. No new option.

## Risks / Trade-offs

**[The first POST was actually delivered, so a retry double-applies]** → The `play-mode`
action is state-targeting (`action: play|pause|stop`), not a queue append, and
`_wait_for_play_state` reconciles the Editor to the target state afterwards. A duplicate
request is a no-op once the Editor is already in the target state (the existing
`already_in_state` / `resumed` transitions cover this).

**[Widening the retry masks a real failure]** → Only the two named transport statuses are
retried; every server-answered non-success is returned on the first body. A scenario in the
delta spec pins this.

**[Exit-code mapping drift between the client and the runtime]** → There is one public
mapping function; the runtime calls it instead of owning a copy, and a regression test
asserts the play-mode envelope's exit code for a representative non-success.
