## Context

This repository already has durable truth for local validation-host wiring and for package-local CLI discovery after installation. What was missing from repository-owned records was a focused real-host run against the published OpenUPM package rather than the local `file:` dependency path.

The experiment against the external validation host established several distinct classes of evidence:

- The host had to be cleaned before the experiment because previous local validation edits were still present.
- OpenUPM package acquisition was blocked until `HTTP_PROXY` / `HTTPS_PROXY` were set to a working local proxy.
- Unity import and domain reload churn made early `exec` attempts look unavailable or noisy even though the same `request_id` later completed successfully once the editor stabilized.
- After import stabilized, the package-local CLI at `Library/PackageCache/com.txcombo.unity-puer-exec@0.1.0/CLI~/unity-puer-exec.exe` successfully executed the representative `BuildBundle` workflow.
- The published package emitted an immutable-package warning about a missing `.meta` under `Packages/com.txcombo.unity-puer-exec/Editor`, which is a product follow-up candidate rather than a validation-recording concern.

This design keeps those facts separate: the current change records the validation truth and the onboarding guidance change, while follow-up product fixes stay outside the scope of this change.

## Goals / Non-Goals

**Goals:**
- Preserve a durable validation record for the published OpenUPM install path rather than leaving the outcome in ephemeral session context.
- Make the real-host validation truth explicitly mention proxy-gated OpenUPM access and import-stabilization waiting as normal environmental concerns.
- Update agent-facing README installation guidance so an agent can recover by asking the user for proxy settings when registry access fails.
- Record follow-up candidates clearly enough that later changes can target them without re-running the whole investigation from scratch.

**Non-Goals:**
- Fix the missing `.meta` packaging issue in this change.
- Change CLI transport shutdown behavior in this change.
- Implement compressed `result_marker` / `brief_sequence` output in this change.
- Expand the default mocked/unit test suite to cover external network or OpenUPM behavior.

## Decisions

### Decision: Treat OpenUPM acquisition friction as product-facing validation evidence

The validation record should not pretend that package acquisition always succeeds on first try. The published package path depends on external registry access, and a real agent can be blocked by missing proxy configuration even when the package itself is correct.

Alternative considered: keep proxy friction out of repository truth because it is "environment-only". Rejected because the README currently provides an installation prompt intended for real agents, and that prompt should help the agent recover from the observed failure mode.

### Decision: Record import stabilization as a required boundary before judging exec usability

The representative workflow should be judged only after Unity has finished the heavy import / domain reload phase triggered by package installation. During that phase, `exec` can time out or the transport can disconnect even though the same request later completes successfully.

Alternative considered: treat the early timeout/noise as a direct product failure. Rejected because the later successful completion on the same request shows the editor was still converging rather than the workflow being intrinsically broken.

### Decision: Keep follow-up defects as explicit candidates instead of folding them into this validation change

The missing immutable-package `.meta` warning, the noisy transport disconnect, and repeated result-marker verbosity are real findings, but they are different scopes of work. Recording them as follow-up candidates preserves the validation outcome without forcing this change to become a mixed implementation umbrella.

Alternative considered: expand this validation change into an umbrella fix-everything change. Rejected because it would blur the evidence record with unrelated implementation decisions and make archive readiness harder to judge.

## Risks / Trade-offs

- [Risk] README guidance could overfit to one proxy setup example. Mitigation: document the recovery pattern generically ("ask the user for proxy settings / set `HTTP_PROXY` and `HTTPS_PROXY` when registry access fails") rather than hardcoding a single environment as universal truth.
- [Risk] Validation truth may understate the packaging warning because the representative workflow still succeeded. Mitigation: record the missing `.meta` warning as an explicit follow-up candidate in the validation notes.
- [Risk] Future OpenUPM behavior may change independently of the product. Mitigation: scope the durable truth to the observed agent workflow and recovery expectations, not to a brittle registry implementation detail.
