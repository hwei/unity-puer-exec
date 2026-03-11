# unity-puer-exec AGENTS

This repository is the productized development repository for `unity-puer-exec`.

## Environment setup

- Before running repository commands that need a Unity project path, load environment variables from `./.env`.
- `UNITY_PROJECT_PATH` points to the validation host Unity project.
- This repository does not assume a repository-local `Project/` directory.

## Path resolution rule

Unity project path resolution must follow this order:

1. explicit `--project-path`
2. `UNITY_PROJECT_PATH`
3. current working directory

## Repo boundary

- Validation host repository: `../c3-client-tree2/`
- Productized development repository: `./`

When a task touches both repositories, explicitly distinguish between the validation host and the productized repository.
