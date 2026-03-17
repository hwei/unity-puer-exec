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
