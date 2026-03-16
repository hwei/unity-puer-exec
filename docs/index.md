# Docs Index

Use this file only to route to the next governance document for the current workflow state.

## Common Reads

- Fresh-session orientation:
  - `docs/workflow.md`
  - `docs/status.md`
  - `docs/roadmap.md`
  - if the current task will lead to substantial implementation, confirm its active `Plan` field before proceeding
- Continuing active work:
  - `docs/status.md`
  - `docs/roadmap.md`
  - the active plan file when one exists
- Executing a roadmap task:
  - `docs/workflow.md`
  - `docs/roadmap.md`
  - confirm the current task has an active executable `Plan`; if not, return to planning instead of implementing
  - then open the active plan file
- Writing or revising a plan:
  - `docs/workflow.md`
  - `docs/planning.md`
  - `docs/plan-template.md`
- Implementing an approved plan:
  - first confirm the current roadmap task has an active plan; if not, return to planning
  - `docs/workflow.md`
  - `docs/roadmap.md`
  - the active plan file
- Retrospective disposition or plan deletion:
  - `docs/workflow-closeout.md`
  - the active plan file
  - `docs/roadmap.md` only when a follow-up task or output pointer must be updated
- Before commit after roadmap work:
  - `docs/workflow-closeout.md`
  - `docs/roadmap.md`
  - confirm whether the current task needs a state, `Plan`, or `Output` update before treating the task execution as closed

## Canonical Roles

- `docs/status.md`: current focus, blockers, next steps
- `docs/roadmap.md`: canonical task graph, task states, dependencies, plan pointers
- `docs/workflow.md`: required sequence and execution-time read path
- `docs/workflow-closeout.md`: closeout rules
- `docs/planning.md`: planning quickstart
- `docs/planning-rules.md`: deeper planning rules
- `docs/plan-template.md`: canonical plan skeleton
- `docs/decisions/`: active durable decisions
