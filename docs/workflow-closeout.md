# Workflow Closeout

Use this file when validating completion, distilling stable conclusions, handling retrospective findings, and deleting a completed plan.

## Distillation Rules

Before deleting a completed plan, move stable conclusions into the right destination:

- `ReadMe.md` for repository purpose, structure, and quick entry points
- `docs/roadmap.md` for active and future work
- `docs/status.md` for current focus, blockers, and next steps
- `docs/decisions/` for active decisions still in force
- source comments when the knowledge is local to specific code or tests

## Retroactive Plan Recovery

If a task was implemented before its plan file existed, recover in this order:

1. create a retroactive task-scoped plan under `docs/plans/` that records the executed scope, agreed constraints, validation, and current closeout state
2. point the roadmap task's `Plan` field at that plan
3. add a `Retrospective` entry to that plan explaining the workflow miss and the suggested follow-up
4. stop and wait for human disposition before reflecting that retrospective into long-lived governance documents

This recovery path is an exception for closeout hygiene only. It does not replace the default requirement to create and review a plan before substantial implementation begins.

## Retrospective Rules

Before deleting a completed plan, the agent should add a brief `Retrospective` section to the active plan file when execution reveals stable follow-up findings or workflow improvement ideas.

- Retrospective findings are discussion inputs, not automatic repository updates.
- The agent should not modify `docs/roadmap.md`, `docs/workflow.md`, `docs/planning.md`, or other long-lived process documents unilaterally based on retrospective findings.
- Each retrospective item should state the observation, why it matters, and the suggested next step.
- Retrospective items remain in the plan until a human explicitly disposes of them.
- Human disposition may accept, defer, reject, or split the finding into follow-up work.
- Accepted findings should be reflected in the appropriate long-lived artifact before the plan is deleted.
- Deferred findings should be preserved in an explicit repo-visible location chosen during human disposition.
- Rejected findings may remain only as disposed notes in the plan and do not require further repository changes.
- If a finding is split into follow-up work, the follow-up task and any required roadmap update should be created before the plan is deleted.
- If execution reveals no retrospective findings, the plan may be deleted without an additional retrospective review step.
- A completed plan should not be deleted while it still contains unresolved retrospective items.
- If a newly discovered issue is required to claim the current task is complete, the agent should raise it before treating the task as done.
