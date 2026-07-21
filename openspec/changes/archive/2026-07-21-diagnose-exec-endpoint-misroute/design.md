## Context

`unity-puer-exec` already has a durable requirement ("Project-scoped commands validate control endpoint identity" in `openspec/specs/formal-cli-contract/spec.md`) that a live endpoint's health identity must be checked against the requested project before it is claimed, "on any port" — including the preferred port. Real-host validation for an unrelated change observed the opposite: `exec --project-path <requested-project>` completed against a different, unrelated project's already-running Editor on the preferred port (55231), while the requested project's own Editor was never launched. The accepted response's `session_marker` matched the unrelated project's `/health` session_marker, and the CLI persisted a `Temp/UnityPuerExec/session.json` under the requested project recording the unrelated project's `base_url`/`unity_pid`/`session_marker`.

Only the symptom was observed and reproduced once (see `openspec/changes/improve-large-response-retrieval/results/validation-evidence.md`). `unity_session.py`'s discovery/claim code has not yet been read to find the actual defect.

## Goals / Non-Goals

**Goals:**

- Read `unity_session.py`'s project-scoped discovery path (`ensure_session_ready` and the code it calls for session-artifact reuse, preferred-port probing, and range-scan discovery) and identify the exact point where a live endpoint's health identity is supposed to be checked against the requested `project_path` but apparently was not, or was checked incorrectly.
- Determine whether `get-log-source`'s separately observed default-log-path/preferred-port fallback (seen when no session artifact yet existed for the requested project) is the same defect, a different defect, or documented/expected fallback behavior per the log-source-resolution contract — do not conflate the two without evidence.
- Once root cause is isolated, fix it so a project-scoped command never claims or persists a session for an endpoint whose live health identity does not match the requested project, on any code path (preferred-port fast path included).
- Add regression coverage: unit tests with mocked health responses simulating "a different project's endpoint is already ready on the preferred port while the requested project has no artifact and is not yet running."

**Non-Goals:**

- Reproducing the exact original three-Unity-process real-host scenario as an automated real-host regression test; a mocked unit reproduction is sufficient evidence for the fix. Real-host reproduction remains optional confirmation.
- Changing the durable spec text unless investigation shows the existing requirement is actually ambiguous or insufficient (see Open Questions).
- Any change to `improve-large-response-retrieval` or its already-committed code; this change is fully independent.

## Decisions

**Root cause (confirmed, reproduced in a mocked unit test):** `unity_session_wait.wait_for_session`'s readiness loop probes `session.base_url` directly and accepts the first payload where `ok` and `status == "ready"` — it never checks the payload's `project_path` against the requested project. Every project-scoped wait site in `ensure_session_ready` (prelaunch recovery, post-claim recovery, cold-start post-launch wait, post-launch-exit recovery) passes an `endpoint_resolver` (`_make_recovery_endpoint_resolver`) that *does* perform identity matching, but the resolver is only consulted to *update* `session.base_url` when it returns a non-`None` candidate. When the resolver returns `None` (no project-matched endpoint found yet, e.g. only an unrelated project answers), the loop falls through to probing whatever `session.base_url` was already set to — which starts out as `direct_exec_client.DEFAULT_BASE_URL` (the preferred port) whenever Phase 1/Phase 2 discovery in `ensure_session_ready` didn't already resolve a project-matched endpoint. If a different, unrelated project is `ready` on that preferred port, this unguarded probe accepts it, and the session (base_url, `unity_pid`, and the persisted artifact) is built from that unrelated project's health payload — reproducing the exact real-host symptom.

This matches expected shape (a) from the original hypothesis: the direct-probe fallback inside the wait loop skips the identity check that the resolver already applies, rather than the artifact-comparison bug from shape (b).

**Fix:** in `wait_for_session`, when `endpoint_resolver is not None` and it returns `None` for an iteration, treat that iteration as "no project-matched endpoint yet" — skip the direct health probe entirely for that iteration (do not fall back to probing the stale `session.base_url`) while still running the launched-process-exit check, stall-timeout check, and poll sleep. This closes all four wait sites at once since they share `wait_for_session`/`_make_recovery_endpoint_resolver`. Call sites with no `endpoint_resolver` (none exist today for project-scoped waits — verified by inspection) are unaffected.

**Related, out-of-scope finding (recorded here, not fixed by this change):** `_has_recoverable_editor_signal` decides whether `ensure_session_ready` enters a recovery wait (instead of launching a new Unity Editor) based on `_list_unity_pids()`, which lists **all** Unity Editor processes on the host, not just ones belonging to the requested project. When an unrelated project's Editor is already running and the requested project has no artifact, this heuristic misfires into a recovery wait for a "recovery" that will never happen. Before this change's fix, that misfire was masked because the wait's unguarded probe would eventually (wrongly) accept the unrelated endpoint as "ready." After the fix, it instead times out with `UnityNotReadyError` without ever attempting `_launch_unity` — trading a silent wrong-project execution for a loud, safe timeout. This is a real usability limitation in the "unrelated project already running, no local artifact" case, but it is not a claim/persist-of-wrong-endpoint defect, so it is out of scope for task 2.1's wording; it is logged as a `product-improvement` follow-up candidate at apply closeout (see closeout summary) rather than fixed here.

**Task 1.3 conclusion — `get-log-source`'s fallback is documented behavior, not a defect:** `openspec/specs/formal-cli-contract/spec.md`'s "Log source resolution supports custom project-scoped paths" requirement states: "Before a valid `session_marker` exists, callers that depend on a non-default log location SHALL provide `--unity-log-path`; otherwise the CLI MAY fall back to the platform default path." `get_log_source` in `unity_session.py` is a pure, read-only path resolver — when no session artifact exists yet, it returns the platform-default Editor log path and `direct_exec_client.DEFAULT_BASE_URL` without probing any endpoint's health or persisting any session artifact. It never claims or asserts that a live endpoint belongs to the requested project, so the "Preferred port is occupied by a different, already-ready project" identity-validation gap does not apply to it — there is nothing to misidentify since it makes no live-endpoint claim at all. No code change is needed for `get-log-source`.

## Risks / Trade-offs

- **[Root cause may span multiple call sites]** → `formal-cli-contract` already describes identity validation as required "at every project-scoped readiness site — initial discovery, any re-probe after a launch claim, recovery waiting, and the wait that follows a cold-start launch." If the defect is in a shared helper, one fix may cover all sites; if not, each site needs its own audit against that requirement text.
- **[Fix could change behavior for legitimately-reused sessions]** → Add regression coverage for the existing "valid artifact endpoint is reused" and "stale artifact endpoint is ignored" scenarios (already specified) alongside the new misroute scenario, so the fix does not regress correct reuse.
- **[Investigation may reveal the durable spec text needs strengthening rather than just the code]** → If so, this change's proposal will be revised in place to add a `project-control-endpoint`/`formal-cli-contract` modified-capability delta before tasks are finalized, rather than silently expanding scope during apply.

## Migration Plan

1. Read the relevant `unity_session.py` code paths against the durable identity-validation requirement; identify the defect with a concrete unit reproduction (mocked health responses).
2. Implement the minimal fix at the identified call site(s).
3. Add regression tests for the misroute scenario plus the existing reuse/staleness scenarios to guard against regression.
4. Optionally confirm against the real host if the mocked reproduction leaves residual doubt.
5. Rollback is reverting the code fix; no persisted state or protocol migration is involved.

## Open Questions

- Is the observed `get-log-source` default-path/preferred-port behavior the same defect as the `exec` misroute, or documented fallback? Must be resolved during investigation before writing tasks that assume a single shared root cause.
- Does the existing durable requirement text need strengthening once the code defect is understood, or is it already sufficient and only the implementation needs to change?
