## 1. Guidance context enrichment

- [ ] 1.1 Extend `_attach_guidance` (or a helper it calls) so that when the payload carries `log_range` with both `start` and `end`, the template context gains a single `log_range_span` value of the form `{start}-{end}`.
- [ ] 1.2 Confirm enrichment reads only CLI-owned envelope fields and invocation args — never script-authored `result` — and leaves candidate selection keyed solely by `(command, status)`.
- [ ] 1.3 Preserve the inject-`log_range`-then-attach-guidance order on `exec` and `wait-for-exec` paths (no reorder that would attach before offsets exist).

## 2. Matrix entries and wait-for-log-pattern wiring

- [ ] 2.1 Author `GUIDANCE_MATRIX` entries for `("exec", "completed")` and `("wait-for-exec", "completed")` with a `get-log-briefs` next_steps candidate using `--range {log_range_span}` and `--levels error,warning`, plus a `when` that frames the sweep as the check for new errors/warnings in the observation window.
- [ ] 2.2 Author `("wait-for-log-pattern", "completed")` with the same error-sweep candidate and a short `situation` stating that a pattern match does not imply the window was free of new errors or warnings.
- [ ] 2.3 Call `_attach_guidance` on the `wait-for-log-pattern` success return after `_inject_log_range_into_payload`, matching the failure-path attach pattern.
- [ ] 2.4 Ensure incomplete context (missing `log_range_span` or `project_path`) omits `argv` but still emits the candidate's `command` and `when`.

## 3. Tests

- [ ] 3.1 Add unit coverage that `exec` / `wait-for-exec` / `wait-for-log-pattern` completed responses with a full `log_range` and project-path selector produce a `get-log-briefs` next_steps entry whose argv contains the concrete range and `--levels error,warning`.
- [ ] 3.2 Assert `wait-for-log-pattern` completed includes the new `situation` text; `exec` / `wait-for-exec` completed do not require a situation.
- [ ] 3.3 Assert that when `log_range` is incomplete, the candidate remains without `argv`.
- [ ] 3.4 Assert two otherwise identical completed envelopes that differ only in script-authored `result` yield the same next_steps candidate set.
- [ ] 3.5 Assert `--suppress-guidance` still strips `next_steps` and `situation` on these success paths.

## 4. Validation and closeout

- [ ] 4.1 Run the targeted unit suite covering the new guidance behavior and confirm green.
- [ ] 4.2 Run `openspec validate fill-success-path-next-steps` and confirm the change remains valid.
- [ ] 4.3 Record the apply closeout finding summary, stating either `No new follow-up work identified` or `New follow-up candidates identified`.
