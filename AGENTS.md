# unity-puer-exec AGENTS

This repository is the productized development repository for `unity-puer-exec`.

## Environment setup

- Repository Python entry points auto-load `./.env` when needed.
- If you set `UNITY_PROJECT_PATH` in the process environment explicitly, that value overrides `./.env`.
- `UNITY_PROJECT_PATH` points to the validation host Unity project.
- This repository does not assume a repository-local `Project/` directory.
- `./.env` is local-only and should not be committed; use `./.env.example` as the tracked template.

## Documentation structure

- `docs/index.md` is the docs-local router by workflow state.
- `docs/workflow.md` defines the required development sequence and implementation-time read path.
- `docs/workflow-closeout.md` defines distillation, retrospective, disposition, and plan-deletion rules.
- `docs/planning.md` is the planning quickstart.
- `docs/planning-rules.md` holds deeper planning rationale and subagent-friendly authoring rules.
- `docs/roadmap.md` tracks active and future work with hierarchical task IDs.
- `docs/status.md` tracks current focus, blockers, and next steps.
- `docs/decisions/` stores active decisions still in force.
- `docs/plans/` stores temporary execution plans only.
- `tests/` is the canonical repository-level test location.

## Path resolution rule

Unity project path resolution must follow this order:

1. explicit `--project-path`
2. `UNITY_PROJECT_PATH` from the process environment
3. repository-local `.env`
4. current working directory

## Repo boundary

- Validation host repository: `../c3-client-tree2/`
- Productized development repository: `./`

When a task touches both repositories, explicitly distinguish between the validation host and the productized repository.
