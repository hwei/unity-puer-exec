# unity-puer-exec AGENTS

This repository is the productized development repository for `unity-puer-exec`.

## Environment setup

- Repository Python entry points auto-load `./.env` when needed.
- If you set `UNITY_PROJECT_PATH` in the process environment explicitly, that value overrides `./.env`.
- `UNITY_PROJECT_PATH` points to the validation host Unity project.
- This repository does not assume a repository-local `Project/` directory.
- `./.env` is local-only and should not be committed; use `./.env.example` as the tracked template.

## Path resolution rule

Unity project path resolution must follow this order:

1. explicit `--project-path`
2. `UNITY_PROJECT_PATH`
3. current working directory

## Repo boundary

- Validation host repository: `../c3-client-tree2/`
- Productized development repository: `./`

When a task touches both repositories, explicitly distinguish between the validation host and the productized repository.
