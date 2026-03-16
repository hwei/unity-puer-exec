# unity-puer-exec AGENTS

This repository is the productized development repository for `unity-puer-exec`.

## Fresh-session workflow

- Start in `docs/index.md`.
- When working on a roadmap task, check `docs/status.md` and `docs/roadmap.md` before implementing.
- Before substantial implementation, confirm the current task has an active plan in its `Plan` field. If no plan exists, return to planning and create one under `docs/plans/`.

## Environment setup

- Repository Python entry points auto-load `./.env` when needed.
- If you set `UNITY_PROJECT_PATH` in the process environment explicitly, that value overrides `./.env`.
- `UNITY_PROJECT_PATH` points to the validation host Unity project.
- This repository does not assume a repository-local `Project/` directory.
- `./.env` is local-only and should not be committed; use `./.env.example` as the tracked template.

## Documentation entry points

- `docs/index.md` routes to the next governance document for the current workflow state.
- `docs/roadmap.md` tracks active and future work with hierarchical task IDs.
- `docs/status.md` tracks current focus, blockers, and next steps.
- `docs/plans/` stores temporary execution plans only.
- `tests/` is the canonical repository-level test location.

## Path resolution rule

Unity project path resolution must follow this order:

1. explicit `--project-path`
2. `UNITY_PROJECT_PATH` from the process environment
3. repository-local `.env`
4. current working directory
