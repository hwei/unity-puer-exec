## Why

The 2026-07-23 external agent validation session, and the interview that reconstructed it, showed that a successful `exec` or `wait-for-log-pattern` leaves the agent without a copyable follow-up: the guidance matrix entries for `("exec", "completed")` and `("wait-for-log-pattern", "completed")` are empty, and a pattern match is easy to misread as "no new errors in that window." The fields needed to construct the right check — `log_range.start` / `log_range.end` — are already on the response; the agent just has to hand-build `get-log-briefs --range … --levels error,warning` from them. That gap was deliberately deferred while `enforce-cli-version-compatibility`, `improve-exec-and-observation-help`, and `normalize-cli-usage-error-responses` landed first; those are now archived, so the success-path guidance change can stack cleanly on the settled matrix and help semantics.

## What Changes

- Author guidance-matrix entries for the success statuses that currently carry empty `next_steps`: `("exec", "completed")`, `("wait-for-exec", "completed")`, and `("wait-for-log-pattern", "completed")`.
- On those statuses, emit a concrete `get-log-briefs` candidate whose `argv` fills `--range {log_range.start}-{log_range.end}` and `--levels error,warning` from CLI-owned response fields, so the agent can re-check the observation window without reconstructing offsets by hand.
- For `wait-for-log-pattern` success only, add a short `situation` stating that a pattern match does not imply the window was free of new errors or warnings.
- Wire `_attach_guidance` on the `wait-for-log-pattern` success path (today it returns without attaching guidance at all).
- Extend guidance construction so `argv` values MAY be drawn from CLI-owned response fields (`log_range`, and other non-script fields already on the envelope). Candidate *selection* remains keyed only by `(command, status)` and MUST NOT inspect script-authored `result`.
- Document that precise split in `runtime-guidance` so a future change does not collapse "fill argv from CLI fields" into "steer candidates from payload."

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `runtime-guidance`: add success-path error-sweep `next_steps` (and the `wait-for-log-pattern` situation), and clarify that argv construction may read CLI-owned response fields while candidate selection stays command+status only.

## Impact

- `cli/python/help_surface.py`: matrix entries for the three `completed` statuses; any shared argv-template placeholders for range ends.
- `cli/python/unity_puer_exec_runtime.py`: enrich guidance context from the response envelope (at least `log_range`); call `_attach_guidance` on `wait-for-log-pattern` success; keep attach-after-`log_range`-inject order so values are present.
- `tests/test_unity_session_cli.py` (and related unit coverage): assert `next_steps` / `situation` on the success paths, argv completeness when `log_range` is present, omission/drop behavior when it is not, and that script `result` does not change candidates.
- No C# / package protocol change: `session_marker` is already present on bridge exec responses; this change does not depend on adding response fields. No new status or exit code. Not **BREAKING**.
