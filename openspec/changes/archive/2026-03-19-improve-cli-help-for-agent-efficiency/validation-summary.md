## Post-Help Validation Summary

Date: 2026-03-20
Model: `gpt-5.4-mini subagent`

## Method

- Re-ran the repository's standard Prompt A scene-editing task after the help-surface refinement.
- Re-ran the repository's standard Prompt B code-write, compile, and verification task after the same help changes.
- Ran the trials sequentially against the same Unity project after baseline reset between tasks so the results remained comparable.
- Restricted discovery to published `unity-puer-exec` help plus normal CLI execution, matching the help-only validation protocol.

## Contamination Note

- An earlier same-day validation attempt ran Prompt A and Prompt B in parallel against the same Unity project.
- Those parallel results are not used as the authoritative comparison evidence for this change because shared-editor contention can distort launch, readiness, compile, and observation behavior.
- The authoritative post-help evidence for this change is the sequential run recorded in:
  - [prompt-a-scene-editing-post-help.yaml](/F:/C3/unity-puer-exec-workspace/unity-puer-exec/openspec/changes/improve-cli-help-for-agent-efficiency/results/prompt-a-scene-editing-post-help.yaml)
  - [prompt-b-menu-compile-verify-post-help.yaml](/F:/C3/unity-puer-exec-workspace/unity-puer-exec/openspec/changes/improve-cli-help-for-agent-efficiency/results/prompt-b-menu-compile-verify-post-help.yaml)

## Prompt A Comparison

- Baseline transcript finding: the earlier simple run probed `ensure-stopped` and `get-log-source` before converging.
- Post-help sequential run: the validating agent stayed on `exec`, `wait-until-ready`, and published example help; it did not probe `ensure-stopped` or `get-log-source`.
- Result: task success passed, autonomy passed, efficiency remained `recoverable`.
- Interpretation: the revised help improved command-level focus for the simple task, but the run still needed extra recovery and script-shape probing after the first exec attempt timed out.

## Prompt B Comparison

- Baseline transcript finding: the earlier long run used `exec`, `wait-until-ready`, `--help-example exec-and-wait-for-result-marker`, and `wait-for-log-pattern`.
- Post-help sequential run: the validating agent stayed on `exec`, `--help-example exec-and-wait-for-result-marker`, and `wait-for-log-pattern`, without probing `ensure-stopped` or `get-log-source`.
- Result: task success passed, autonomy passed, efficiency remained `recoverable`.
- Interpretation: the revised help preserved a focused long-task command path and avoided secondary troubleshooting help, but the run still needed a second observation attempt because the first wait started after the target log line had already been emitted.

## Overall Assessment

- The help refinement improved command discoverability for both representative task classes by keeping the agent on the intended primary and supporting command path.
- The earlier simple-task detour into `ensure-stopped` and `get-log-source` did not recur in the sequential post-help evidence.
- The post-help long task also avoided those secondary help surfaces and remained focused on `exec` plus log observation.
- Both tasks still scored `recoverable` rather than `clean`, so the current improvement is meaningful but not yet sufficient to claim clearly clean convergence across the representative set.

## Recommended Next Step

- Keep this change open.
- Use the sequential post-help evidence to target the remaining recovery and observation-timing friction, especially around first-try readiness timing for project-scoped exec and first-try log observation setup for verification workflows.
- Track the deeper timeout-ambiguity and recovery-contract work under `improve-exec-timeout-recovery-observability` instead of expanding this help-focused change further.
