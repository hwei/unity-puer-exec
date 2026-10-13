## Context

The play path documents that it re-resolves a dropped endpoint within a bound. That retry is
implemented in `_post_play_mode` and keyed off `_is_play_mode_transport_drop(body)`, which is
defined **over an already-parsed body**:

```python
def _is_play_mode_transport_drop(body):
    if body is None:
        return True
    if body.get("http_status") == 404:
        return False
    return body.get("status") in (STATUS_EMPTY_RESPONSE, "not_available")
```

The retryable statuses are produced by `direct_exec_client.invoke_command`, whose four
handlers are `urllib.error.HTTPError`, `urllib.error.URLError`, `ValueError`, and
`socket.timeout`. A peer reset matches none of them.

The archived reproduction already verified the exception hierarchy and the exact envelope, so
this change does not re-derive the mechanism; it fixes the classification.

## Goals / Non-Goals

**Goals:**

- Make a peer reset produce a retryable transport body so the existing `_post_play_mode` bound
  applies to it.
- Keep the classification in one place — the transport boundary — rather than adding
  per-caller try/except wrappers.

**Non-Goals:**

- Not auditing every `invoke_command` caller; that is
  `classify-peer-reset-on-all-transport-callers`.
- Not changing the bound, the retry cadence, or the exit-code mapping.
- Not adding resilience to `HttpTransport` itself (e.g. retrying inside `post_json`); the
  retry contract belongs to the command, not the transport.

## Decisions

### Decision 1: Fix the boundary, not the callers

`invoke_command` already converts transport conditions into structured payloads for four
exception families. A peer reset belongs in that same family, so `_post_play_mode` — and every
other caller — inherits the fix without per-site handling.

### Decision 2: Map to `not_available`, matching the existing `URLError` treatment

A reset connection means the endpoint is not answering, which is exactly what
`not_available` already denotes in this codebase, and it maps to `EXIT_NOT_AVAILABLE` (12).
The alternative of introducing a new status would widen the public status surface and require
help-surface and exit-code updates for no behavioral gain.

### Decision 3: Catch `OSError`/`ConnectionError` and `http.client.HTTPException` explicitly

`RemoteDisconnected` inherits from both `ConnectionResetError` (an `OSError`) and
``BadStatusLine` (an `HTTPException`), so either base catches this specific case. Catching both
bases also covers sibling conditions — `BadStatusLine` for a garbage response line,
`ConnectionAbortedError` / `ConnectionRefusedError` — which are the same "the endpoint is not
answering" class. The implementation should verify the sibling cases behave sensibly rather
than assuming.

### Decision 4: Preserve the reset text for diagnosis

The existing `URLError` handler puts `str(exc.reason)` into `error`. The reset case should keep
the underlying text reachable (so `WinError 10054` still appears for diagnosis) while
normalizing the status to `not_available`. Losing the errno detail would make the next
occurrence harder to recognize — the exact failure mode this investigation had to undo.

## Risks / Trade-offs

**Catching `OSError` is broad** → it can swallow local errors such as a bad hostname or a
missing socket. Mitigated by only adding the classes that cannot occur locally for a valid
loopback request, and by asserting the resulting status in tests. The task list requires
verifying this rather than assuming it.

**A retry now happens where previously it failed fast** → a genuine endpoint outage will retry
until the bound elapses rather than returning immediately. That is the documented intent for
this path, but the bound should be confirmed to be short enough that a hard outage is not
made worse by the change.