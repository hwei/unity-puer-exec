# Project Path Resolution Plan

## Background

`unity-puer-exec` has already been split out from the validation host repository. Keeping repository-scoped path assumptions such as `PROJECT_ROOT` and `PROJECT_DIR` in runtime code would reintroduce coupling between:

- the productized development repository: `unity-puer-exec`
- the validation host repository: `c3-client-tree2`

The current issues are:

1. Runtime code still assumes the Unity project may live under the current repository.
2. Tests still contain hardcoded legacy host project paths.
3. The repository does not yet define a stable contract for how agents and scripts should obtain `UNITY_PROJECT_PATH`.

## Goal

Define one explicit project path resolution model and remove repository hardcoding:

- remove `PROJECT_ROOT` and `PROJECT_DIR` from runtime code
- make `--project-path` the highest-priority CLI input
- when `--project-path` is absent, use environment variable `UNITY_PROJECT_PATH`
- when the environment variable is absent, fall back to the current working directory
- make tests stop hardcoding Unity project paths
- add `unity-puer-exec/.env` to record the current `UNITY_PROJECT_PATH`
- add `unity-puer-exec/AGENTS.md` to document the `.env` loading rule for this repository

## Repository Scope

This plan intentionally puts the environment contract inside `unity-puer-exec`, not at the workspace root.

Reasoning:

- the workspace root is only a temporary multi-repo migration container
- `UNITY_PROJECT_PATH` is a runtime contract for `unity-puer-exec`, not for the whole workspace
- repository-local `.env` and `AGENTS.md` can move together if this repo is later extracted from the current workspace layout
- this matches the existing rule that the more local `AGENTS.md` should take precedence

## Planned Changes

### 1. Runtime Path Resolution

Update [unity_session.py](F:\C3\unity-puer-exec-workspace\unity-puer-exec\.claude\skills\unity-puer-exec\unity_session.py):

- remove `PROJECT_ROOT` and `PROJECT_DIR`
- add a single project path resolution function
- apply this precedence:
  1. explicit function argument `project_path`
  2. environment variable `UNITY_PROJECT_PATH`
  3. `Path.cwd()`
- keep `_get_unity_version()` behavior unchanged after it receives the resolved final path

### 2. CLI Resolution Rules

Update [unity_session_cli.py](F:\C3\unity-puer-exec-workspace\unity-puer-exec\.claude\skills\unity-puer-exec\unity_session_cli.py):

- stop using a repository constant as the `--project-path` default
- keep `--project-path` optional
- resolve the final path at runtime instead of in `argparse`
- make the help text explicit about precedence:
  - `--project-path`
  - `UNITY_PROJECT_PATH`
  - current working directory

### 3. Test Updates

Update:

- [test_unity_session.py](F:\C3\unity-puer-exec-workspace\unity-puer-exec\.claude\skills\unity-puer-exec\tests\test_unity_session.py)
- [test_unity_session_cli.py](F:\C3\unity-puer-exec-workspace\unity-puer-exec\.claude\skills\unity-puer-exec\tests\test_unity_session_cli.py)

Planned test split:

- pure unit tests:
  - remove hardcoded `F:/C3/...` Unity project paths
  - use neutral sample paths or direct resolution assertions
- tests that truly require a real Unity project path:
  - read `UNITY_PROJECT_PATH`
  - fail clearly when `UNITY_PROJECT_PATH` is missing

Implementation note:

- only tests that actually need to read `ProjectSettings/ProjectVersion.txt` should depend on the environment variable
- fully mocked tests should remain independent from any real Unity project directory

### 4. Repository-Local Environment Contract

Add the following files in `unity-puer-exec`:

- [AGENTS.md](F:\C3\unity-puer-exec-workspace\unity-puer-exec\AGENTS.md)
- `.env`

Contract to document:

- this repository uses `UNITY_PROJECT_PATH` to point to the validation host Unity project
- agents working inside this repository must load environment variables from `unity-puer-exec/.env` before running related commands
- documentation must clearly distinguish:
  - validation host repository: `c3-client-tree2`
  - productized development repository: `unity-puer-exec`

### 5. Repository Documentation

Update [ReadMe.md](F:\C3\unity-puer-exec-workspace\unity-puer-exec\ReadMe.md):

- remove any wording that implies the default Unity project path is the repository-local `Project/`
- document the new path resolution model at a high level

## Validation Steps

The implementation will be validated by directly executing the following steps.

### 1. Run unit tests

Command:

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

Working directory:

```text
F:\C3\unity-puer-exec-workspace\unity-puer-exec\.claude\skills\unity-puer-exec
```

Expected result:

- all unit tests pass

### 2. Verify explicit CLI argument precedence

Command:

```powershell
$env:UNITY_PROJECT_PATH='F:\C3\unity-puer-exec-workspace\c3-client-tree2\Project'
python unity_session_cli.py ensure-ready --project-path X:\explicit-project --health-timeout-seconds 0.1
```

Working directory:

```text
F:\C3\unity-puer-exec-workspace\unity-puer-exec\.claude\skills\unity-puer-exec
```

Expected result:

- the resolved project path is `X:\explicit-project`
- the environment variable does not override the explicit CLI argument

### 3. Verify environment variable precedence

Command:

```powershell
$env:UNITY_PROJECT_PATH='F:\C3\unity-puer-exec-workspace\c3-client-tree2\Project'
python unity_session_cli.py ensure-ready --health-timeout-seconds 0.1
```

Working directory:

```text
F:\C3\unity-puer-exec-workspace\unity-puer-exec\.claude\skills\unity-puer-exec
```

Expected result:

- when `--project-path` is not provided, the code uses `UNITY_PROJECT_PATH`
- the implementation no longer depends on any repository-local hardcoded `Project/` path

### 4. Verify CWD fallback

Command:

```powershell
Remove-Item Env:UNITY_PROJECT_PATH -ErrorAction SilentlyContinue
python unity_session_cli.py ensure-ready --health-timeout-seconds 0.1
```

Working directory:

- either a real Unity project directory for a success path validation
- or a controlled temporary directory for a failure path validation

Expected result:

- when both the CLI argument and environment variable are absent, the code uses `Path.cwd()`

### 5. Verify repository-local environment documentation

Check all of the following:

- `F:\C3\unity-puer-exec-workspace\unity-puer-exec\.env` exists
- [AGENTS.md](F:\C3\unity-puer-exec-workspace\unity-puer-exec\AGENTS.md) documents the `.env` loading rule
- [ReadMe.md](F:\C3\unity-puer-exec-workspace\unity-puer-exec\ReadMe.md) no longer describes repository-local `Project/` as the default runtime path

## Acceptance Criteria

This plan is complete only when all of the following are true:

- runtime code no longer hardcodes `PROJECT_ROOT` or `PROJECT_DIR`
- CLI path resolution follows:
  1. `--project-path`
  2. `UNITY_PROJECT_PATH`
  3. current working directory
- tests no longer contain the legacy hardcoded Unity host project path
- `unity-puer-exec/.env` exists and records `UNITY_PROJECT_PATH`
- `unity-puer-exec/AGENTS.md` documents the repository-local `.env` rule
- unit tests pass
- after implementation is complete, this temporary plan document is deleted before the final implementation commit

## Commit Plan

After plan approval, execution will use two commits:

1. commit this plan document
2. implement the changes, validate them, delete this plan document, and commit the final implementation
