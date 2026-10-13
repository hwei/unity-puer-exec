## Why

A real-host play failure (`test_play_settles_a_pending_change_then_reaches_playing`, archived
change `2026-10-13-validate-real-host-refresh-trigger-extension`) reported:

```
{'ok': False, 'status': 'failed', 'operation': 'play', 'error': '[WinError 10054] ...', 'cli_version': '0.9.0'}
```

with exit code `1`. The documented contract says a dropped endpoint on the play path is
retried within the command's bound and, if it does not recover, reported as a structured
non-success state with its formal exit code — never a generic failure.

The archived investigation `2026-10-13-reproduce-play-mode-transport-reset-flake` established
deterministically that this is not a bound problem and not environmental. When the Editor
resets a connection without writing a status line, CPython raises
`http.client.RemoteDisconnected`. Its MRO is
`RemoteDisconnected → ConnectionResetError → ConnectionError → OSError` plus
`BadStatusLine → HTTPException`; it is **not** a subclass of `urllib.error.URLError`,
`ValueError`, or `socket.timeout`, which are the only handlers
`direct_exec_client.invoke_command` has. The exception therefore escapes `invoke_command`,
escapes the `while True` body of `_post_play_mode`, and is normalized by the top-level
`except Exception` in `run_cli` to `status: "failed"` / exit `1`.

Consequence: the retry branch in `_post_play_mode` is **unreachable** for a peer reset. No
bound, however long, can cover this condition.

## What Changes

- Classify a peer reset / connection-reset transport failure as a transport drop rather than
  letting it escape `direct_exec_client.invoke_command`.
- Extend the `play-mode-control` transport contract so "dropped endpoint" explicitly covers
  a reset connection, not only an empty or unparseable body.
- Add regression coverage at the boundary.

## Capabilities

### Modified Capabilities

- `play-mode-control` — the "Play-mode commands recover a dropped control endpoint"
  requirement currently names only an empty/unparseable response body as the drop condition.
  A peer reset produces no body at all, so it falls outside the requirement and escapes the
  retry entirely.

## Impact

- Affected code: `cli/python/direct_exec_client.py` (the transport boundary).
- Affected specs: `openspec/specs/play-mode-control/spec.md`.
- Affected validation: unit coverage for the boundary classification.
- Evidence: `openspec/changes/archive/2026-10-13-reproduce-play-mode-transport-reset-flake/`
  (`finding.md`, plus the committed reproduction `repro_play_transport_reset.py` and its
  transcript `repro_play_transport_reset.log`).