## Current Baseline Revalidation Summary

Date: 2026-03-23
Model: `gpt-5.4-mini subagent`

## Method

- Reused the archived Prompt A scene-editing task without changing the goal wording.
- Reused the archived Prompt B code-write, compile, and verification task without changing the goal wording.
- Ran the trials sequentially against the same Unity validation host project from `.env`.
- Restricted discovery to published `unity-puer-exec` help plus normal CLI execution, while treating environment friction as part of the product-facing outcome.
- Kept raw transcript retention optional; this durable record is based on the subagents' structured final reports.

## Prompt A Comparison

- Archived baseline finding: the first-round run succeeded but included extra exploration and modal-blocker contamination from the earlier unnamed-scene workflow.
- Archived post-help finding: the later run stayed on the intended `exec` plus `wait-until-ready` path and avoided `ensure-stopped` and `get-log-source`, but still remained `recoverable` because the first `exec` timed out before readiness.
- Current run: the validating agent stayed on `exec`, `wait-until-ready`, and blocker diagnostics, and it did not probe `ensure-stopped` or `get-log-source`.
- Current result: task success passed, autonomy passed, efficiency remained `recoverable`.
- Interpretation: command-level focus remained improved relative to the earliest baseline, but the CLI still did not provide a clean first-pass startup path and the agent needed several bridge-shape probes before it could complete the actual edit.

## Prompt B Comparison

- Archived baseline finding: the first-round long task succeeded through `exec`, `wait-until-ready`, published examples, and log-based verification.
- Archived post-help finding: the later run stayed focused on `exec` plus the intended supporting help surfaces, but still remained `recoverable` because the first observation attempt started too late and required a second execution path.
- Current run: the validating agent again stayed on the intended primary and supporting command family without probing unrelated troubleshooting commands.
- Current result: task success passed, autonomy passed, efficiency remained `recoverable`.
- Interpretation: the CLI still supports autonomous multi-step completion, but a clean verification path is still not obvious or robust enough because compile timing, selection timing, and final observation all required additional recovery or fallback work.

## Overall Assessment

- The current CLI still passes the repository's two basic help-only agent workflows with the fixed `gpt-5.4-mini subagent` baseline.
- The help-surface command focus remains better than the earliest archived baseline because neither task detoured into `ensure-stopped` or `get-log-source`.
- Both workflows still land at `recoverable` rather than `clean`.
- Environment friction remains product-facing and material:
  - Prompt A required explicit startup recovery after the first project-scoped `exec` failed to bring Unity to readiness.
  - Prompt B required compile recovery, selection-state debugging, and a final fallback outside the intended CLI observation path.
- This means the CLI is still usable for autonomous baseline workflows, but it has not yet reached the stronger goal of clean, first-pass autonomous Unity task closure.

## Follow-Up Readout

- New follow-up candidates identified: `product-improvement`
- Candidate 1: Reduce first-pass project-scoped startup failure and readiness recovery friction for `exec`.
- Candidate 2: Make verification workflows more robust so agents can confirm results without falling back to direct host-file or host-log inspection.
