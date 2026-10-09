> **Superseded** by `make-base-url-exec-refresh-recoverable` (2026-10-09), which absorbs this
> change's help requirement and tasks so the wording matches the chosen base-url continuation.
> Archive this change without applying it.

## Why

The `exec` help surface describes `--wait-timeout-ms` as "how long to wait before returning
the current execution state" and tells the caller the command may return `running` "when the
wait budget ends before the request finishes". Nothing says that an automatic refresh's
compile cycle settles on a separate, compile-scale budget. A caller therefore reasonably
concludes that a small `--wait-timeout-ms` bounds the whole call, refresh included.

That wrong mental model has already cost us a defect. The real-host regression for base-url
automatic refresh encoded exactly it (`WAIT_TIMEOUT_MS = 1000` for a case whose first exec
triggers a refresh), and `diagnose-exec-missing-after-auto-refresh` had to add a
`REFRESH_WAIT_TIMEOUT_MS = 300_000` constant with a code comment explaining that an exec "has
to give the CLI's internal settle+resubmit loop enough budget". A caller should learn that
from help, not from the test suite or the source.

`exec --help-status` is consistent with the incomplete model: it names the `refreshing` and
`compiling` phases without saying that reaching a settled state is not bounded by the
request-wait budget.

## What Changes

- State, wherever `exec` describes its wait or timeout behavior, that an automatic refresh's
  compile cycle is settled on its own compile-scale budget.
- State that `--wait-timeout-ms` does not bound that settle, so a caller choosing a small
  request-wait budget knows a refresh is not abandoned at that value.
- Make `exec --help-status` consistent with the same statement.
- Add regression assertions on the help surfaces so the statement cannot be dropped silently
  again.
- No runtime behavior change: this states what the CLI already does after
  `diagnose-exec-missing-after-auto-refresh`.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `formal-cli-contract`: adds a requirement in the same family as "Help states that only code
  changes trigger automatic refresh" — help must state that an automatic refresh settles on
  its own compile-scale budget and is not bounded by `--wait-timeout-ms`, on every surface
  that describes `exec`'s wait or timeout behavior.

## Impact

- Affected code: `cli/python/help_surface.py` (the `exec` option list, "Automatic refresh"
  line, "Timeout Rules", and the `--help-status` status section), plus
  `cli/python/unity_puer_exec_surface.py` if the statement also belongs in an argument's
  `help=` text.
- Affected behavior: caller-visible documentation only. No command's response, exit code, or
  timing changes.
- Affected validation: `tests.test_unity_session_cli` help-content cases;
  `tests.test_openspec_spec_hygiene` guards the durable delta's structure.
- Relationship: the sibling help requirement for the code-only trigger boundary is
  unchanged; `wait-for-compile --settle-timeout-seconds` already documents the equivalent
  budget on its own surface and should stay the consistent reference.
