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

To be filled in once the root cause is identified. Expected shape: either (a) the preferred-port direct-probe path skips the identity check that the range-scan path applies, and the fix aligns the two paths, or (b) the identity check exists but compares against stale/incorrect state (e.g. compares the artifact's own recorded `project_path` instead of the live `/health` response's `project_path`). This section will record the actual decision and the code path once confirmed, plus any alternatives considered.

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
