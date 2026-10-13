# Finding: the play-path transport reset is not environmental — the retry branch is unreachable

**Disposition: reproducible gap in the transport branch selection (not an environmental
flake, and not a retry-bound problem).**

## 1. The recorded observation

From `.tmp/realhost_rest_run.log` (archived change
`2026-10-13-validate-real-host-refresh-trigger-extension`), one case in a 32-test
real-host run, `Ran 32 tests in 1820.745s`, `FAILED (failures=1, skipped=3)`:

```
FAIL: test_play_settles_a_pending_change_then_reaches_playing
  File "tests/test_real_host_integration.py", line 3848, in test_play_settles_a_pending_change_then_reaches_playing
    self.assertEqual(exit_code, 0, payload)
AssertionError: 1 != 0 : {'ok': False, 'status': 'failed', 'operation': 'play',
  'error': '[WinError 10054] <zh: remote host forcibly closed an existing connection>',
  'cli_version': '0.9.0'}
```

Facts established from the transcript rather than from recollection:

- **Exit shape:** `1`, with `status: "failed"` — *not* `12` / `not_available`, which is
  what this CLI's documented transport boundary emits for an unreachable endpoint.
- **Retry was never attempted.** The failure is a single terminal envelope, not an
  exhausted bounded retry.
- **No boundary report exists for this case.** The four `[real-host-boundary]` lines in
  the transcript belong to other cases (`batch_mode_one_shot_processes`,
  `cold_launch_retry`, `preferred_port_rollover`, `preferred_port_rollover_discovery`),
  and two of them explicitly record `"mid_reload_rebind": "not_staged"`. So no
  deliberately staged reload edge preceded the failure.
- On immediate retry the same case passed in 140.310s (`.tmp/realhost_play_retry.log`).

The `status: "failed"` value is the discriminator. In `cli/python/unity_puer_exec_runtime.py`
only two sites produce it: the Unity-side internal-error body
(`{"ok":false,"status":"failed","error":"internal_error"}`, which this error is not), and
`unexpected_failure_payload` at line 476, reached solely from the catch-all
`except Exception` in `run_cli` (line 628). So the payload proves **an uncaught Python
exception reached the top level** — the play path never produced a structured transport
body for `_post_play_mode` to act on at all.

## 2. The branch the observed error would have taken

`_post_play_mode` (line 2430) retries only when `_is_play_mode_transport_drop(body)` is
true, and that predicate (line 2418) is defined **over an already-parsed body**:

```python
def _is_play_mode_transport_drop(body):
    if body is None:
        return True
    if body.get("http_status") == 404:
        return False
    return body.get("status") in (STATUS_EMPTY_RESPONSE, "not_available")
```

The retryable statuses are produced by `direct_exec_client.invoke_command`, whose four
except clauses (lines 173–205) are `urllib.error.HTTPError`, `urllib.error.URLError`,
`ValueError`, and `socket.timeout`.

**The peer-reset exception is none of these.** When the Editor's listener accepts the
connection and then resets it without writing a status line, CPython raises
`http.client.RemoteDisconnected` from `HTTPConnection.getresponse`. On Windows it is
constructed with the `ConnectionResetError(10054, ...)` from the socket read — verified
in this repo's Python:

```
RemoteDisconnected MRO: RemoteDisconnected → ConnectionResetError → ConnectionError → OSError
                             → BadStatusLine → HTTPException
issubclass(RemoteDisconnected, urllib.error.URLError) == False
issubclass(RemoteDisconnected, ValueError)        == False
issubclass(RemoteDisconnected, socket.timeout)     == False
```

So it matches no handler, propagates out of `invoke_command`, out of `_post_play_mode`'s
`while True` loop, out of `_run_play_mode_command`, and is caught by the top-level
`except Exception`, which emits `status: "failed"` / exit 1.

## 3. Deterministic reproduction

Tracked with this change as `repro_play_transport_reset.py`, with its output committed
as `repro_play_transport_reset.log`. It is read-only: it monkeypatches the transport
in-process and writes no file and no product code, so it can be re-run after the change
is archived to confirm the reproduction still holds. (`python repro_play_transport_reset.py`,
run from anywhere — it locates the repository root itself.)

```
== Which exceptions does invoke_command() convert to a retryable status? ==
  urllib URLError        status='not_available'    retryable=True
  RemoteDisconnected     ESCAPED RemoteDisconnected -> NOT retryable
  ConnectionResetError   ESCAPED ConnectionResetError -> NOT retryable
  socket.timeout         status='not_available'    retryable=True
  ValueError (bad body)  status='empty_response'   retryable=True

== Does the escaped exception reach the observed payload shape? ==
  exit_code: 1
  stdout:    {"ok": false, "status": "failed", "operation": "play",
              "error": "[Errno 10054] remote host forcibly closed an existing connection",
              "cli_version": "0.9.0"}
  matches the observed real-host envelope shape: True
```

Side by side, the only textual difference between the real-host failure in §1 and the
reproduced payload is the errno prefix — `[WinError 10054]` versus `[Errno 10054]` — which
is CPython's Windows/other-platform wording for the same `errno 10054`:

```
real host   {'ok': False, 'status': 'failed', 'operation': 'play',
             'error': '[WinError 10054] <zh>', 'cli_version': '0.9.0'}
reproduced  {"ok": false, "status": "failed", "operation": "play",
             "error": "[Errno 10054] remote host forcibly closed an existing connection",
             "cli_version": "0.9.0"}
```

The full propagation chain, quoted from this repository:

| # | Site | Behavior on the peer reset |
|---|---|---|
| 1 | `direct_exec_client.HttpTransport.post_json` (`direct_exec_client.py:73`) | `opener.open(...)` raises `RemoteDisconnected`; no handler here |
| 2 | `direct_exec_client.invoke_command` (`:169`) | handlers are `HTTPError`, `URLError`, `ValueError`, `socket.timeout` (`:173`–`:205`); none match |
| 3 | `_post_play_mode` (`:2444`) | `invoke_command` raises out of the `while True` body; the retry branch at `:2455`–`:2463` is never reached |
| 4 | `_run_play_mode_command` (`:2813`) | the call at `:2813` raises; every `body`-shaped result branch below it is skipped |
| 5 | `run_cli` (`:628`) | `except Exception` → `unexpected_failure_payload` (`:476`) → `status: "failed"`, exit `1` |

Step 3 is the important one: because the exception leaves `_post_play_mode` rather than
returning a body, the retry logic is not merely insufficient — it is unreachable for
this condition.

Two consequences worth stating explicitly:

1. The bound is **irrelevant**. Even an unbounded retry loop would not help: the retry
   lives *inside* `_post_play_mode`, which never receives control again once the
   exception propagates. The premise in the proposal — "the bound is too short, or the
   drop landed outside the retrying branch" — resolves to the second case: the drop
   lands outside the retrying branch, and not narrowly.
2. `probe_health` (`unity_session_wait.py:26`) does catch `Exception` and degrade to
   `(None, str(exc))`, so the health-probe path is safe. The exposure is specific to
   paths that call `invoke_command` without their own blanket handler.

Per the design's Decision 2, no product code was changed. Proposed follow-up:

## 4. Recommended separate product change (NOT implemented here)

`recover-peer-reset-transport-drop`, whose fix is to widen the boundary in
`direct_exec_client.invoke_command` so a peer reset is classified as a transport drop
rather than escaping:

- Catch `http.client.HTTPException` and `ConnectionError` alongside the existing clauses
  and map them to `not_available` (matching the existing `URLError` treatment), so
  `_is_play_mode_transport_drop` sees a retryable body and `_post_play_mode` retries
  within its existing bound.
- Re-check the expectation in `tests/test_real_host_reset.py:90`, which currently asserts
  the `probe_health` `WinError 10054` path; the new `invoke_command` coverage should sit
  beside it.
- Durable-spec delta needed: `play-mode-control` should state that a peer reset is a
  transport drop, not an unexpected failure.

The evidence for that change is this document plus `repro_play_transport_reset.py` and
`repro_play_transport_reset.log`. The fix was deliberately not applied here so that the
reproduction stays reproducible.

## 5. Apply closeout review

**New follow-up candidates identified.**

### Candidate A — `recover-peer-reset-transport-drop` (`product-improvement`)

The gap described in §4. Proposed as a separate change, with this finding as its evidence.
Raised for human discussion; **not** created and **not** implemented in this session.

### Candidate B — `invoke_command` transport-classification coverage (`validation-gap`)

The `play` path is where the flake surfaced, but `_post_play_mode` is only one of several
callers of `direct_exec_client.invoke_command`. This investigation read
`probe_health` (safe: blanket `except Exception`) and `invoke_command` (exposed), but did
not audit every remaining caller for an equivalent unprotected path. The same escape would
present identically as `status: "failed"` on any of them. A follow-up should sweep the
callers and assert the boundary classification directly.

### Candidate C — closeout review of the archived change's assumption (`workflow-improvement`)

`2026-10-13-validate-real-host-refresh-trigger-extension` recorded this failure as belonging
to "that flake class" — the intermittent launch-recovery / empty-response class of
environmental flakes. This finding contradicts that classification: the play-path instance
is a deterministic code-path gap, reproducible without a host. The archive is immutable, but
the flake-class bucket may be conflating environmental noise with an unclassified transport
class, which risks a future real bug being filed as environmental.

**Disposition: dropped by human review (2026-10-13).** Raised during closeout, then declined:
the archived record already carries the corrected classification, and a standalone change for
a process observation was judged to carry no code or durable-spec value. Noted here so the
reasoning is not lost and re-raised in a later session.

## 6. Verification evidence

- Default suite green: `python -m unittest discover -s tests` → `Ran 730 tests in 39.135s`, `OK (skipped=3)`.
- `openspec validate reproduce-play-mode-transport-reset-flake --strict` →
  `Change 'reproduce-play-mode-transport-reset-flake' is valid`, with the expected
  `skip_specs` informational line.
- `openspec validate --all` → `Totals: 32 passed, 0 failed (32 items)`.
- No product code changed: `git status` shows only files inside this change's directory.
- Durable reproduction: `repro_play_transport_reset.py` + `repro_play_transport_reset.log`.
  The original failure transcript is local-only and is quoted verbatim in §1 above so the
  record does not depend on `.tmp/`:
  `.tmp/realhost_rest_run.log` (failure), `.tmp/realhost_play_retry.log` (retry pass).