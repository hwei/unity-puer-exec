# Zero-Dependency .env Autoload Plan

## Background

`unity-puer-exec` already defines a repository-local `.env` file and a repository-local `AGENTS.md` rule that tells agents to load `UNITY_PROJECT_PATH` before running related commands.

That contract works, but it still depends on the caller remembering to export the variable manually before invoking Python entry points.

The next step is to make the repository load `.env` automatically, without introducing a new Python dependency such as `python-dotenv`.

## Goal

Add repository-local `.env` autoload behavior with no new third-party Python library.

The implementation should:

- load `.env` from the `unity-puer-exec` repository root
- support the simple `KEY=VALUE` format currently used by this repository
- populate environment variables only when they are not already set
- preserve existing precedence:
  1. explicit `--project-path`
  2. `UNITY_PROJECT_PATH` from process environment
  3. `UNITY_PROJECT_PATH` loaded from `.env`
  4. current working directory
- stop tracking machine-local `.env`
- keep a tracked `.env.example` as the repository template

## Non-Goals

This plan does not attempt to implement full `.env` compatibility.

Specifically, it will not add support for:

- advanced quoting rules
- shell interpolation
- multiline values
- variable expansion
- external Python packages

## Planned Changes

### 1. Add a small internal `.env` loader

Update [unity_session.py](F:\C3\unity-puer-exec-workspace\unity-puer-exec\.claude\skills\unity-puer-exec\unity_session.py):

- add a helper that finds the repository root from the current module path
- add a helper that reads `unity-puer-exec/.env`
- parse only the simple `KEY=VALUE` lines needed for this repository
- ignore blank lines and comment lines
- do not overwrite variables that already exist in `os.environ`

### 2. Normalize repository `.env` file strategy

Update:

- [`.gitignore`](F:\C3\unity-puer-exec-workspace\unity-puer-exec\.gitignore)
- `unity-puer-exec/.env`
- `unity-puer-exec/.env.example`

Planned behavior:

- add `.env` to `.gitignore`
- stop tracking the machine-local `.env`
- add a tracked `.env.example` with the same key name and a documented placeholder value
- keep the autoload logic reading `.env`, not `.env.example`

### 3. Hook autoload into runtime resolution

Update [unity_session.py](F:\C3\unity-puer-exec-workspace\unity-puer-exec\.claude\skills\unity-puer-exec\unity_session.py):

- ensure `.env` loading happens before project path resolution reads `UNITY_PROJECT_PATH`
- keep the path resolution API explicit and testable
- avoid global side effects at import time unless they are narrow and deterministic

Preferred implementation direction:

- trigger `.env` loading lazily from the project path resolution flow
- keep the loader idempotent so repeated calls stay safe

### 4. Extend tests

Update:

- [test_unity_session.py](F:\C3\unity-puer-exec-workspace\unity-puer-exec\.claude\skills\unity-puer-exec\tests\test_unity_session.py)
- [test_unity_session_cli.py](F:\C3\unity-puer-exec-workspace\unity-puer-exec\.claude\skills\unity-puer-exec\tests\test_unity_session_cli.py) if needed

Add tests for:

- `.env` values are loaded when the process environment does not already contain `UNITY_PROJECT_PATH`
- existing process environment values are not overwritten by `.env`
- blank lines and comment lines are ignored
- path resolution still prefers explicit `--project-path`
- path resolution still prefers process environment over `.env`
- the tracked `.env.example` does not interfere with runtime loading

### 5. Update repository documentation

Update:

- [AGENTS.md](F:\C3\unity-puer-exec-workspace\unity-puer-exec\AGENTS.md)
- [ReadMe.md](F:\C3\unity-puer-exec-workspace\unity-puer-exec\ReadMe.md)

Document that:

- the repository now auto-loads `.env` for its own Python entry points
- `.env` is local-only and should not be committed
- `.env.example` is the tracked template
- explicit environment variables still override `.env`
- explicit CLI arguments still override both

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

### 2. Verify `.env` is used when process environment is unset

Command:

```powershell
Remove-Item Env:UNITY_PROJECT_PATH -ErrorAction SilentlyContinue
@'
import unity_session
print(unity_session.resolve_project_path())
'@ | python -
```

Working directory:

```text
F:\C3\unity-puer-exec-workspace\unity-puer-exec\.claude\skills\unity-puer-exec
```

Expected result:

- the resolved path equals the `UNITY_PROJECT_PATH` value from `unity-puer-exec/.env`

### 3. Verify process environment overrides `.env`

Command:

```powershell
$env:UNITY_PROJECT_PATH='X:\from-process-env'
@'
import unity_session
print(unity_session.resolve_project_path())
'@ | python -
```

Working directory:

```text
F:\C3\unity-puer-exec-workspace\unity-puer-exec\.claude\skills\unity-puer-exec
```

Expected result:

- the resolved path is `X:\from-process-env`
- the `.env` value does not overwrite the existing process environment value

### 4. Verify explicit argument still wins

Command:

```powershell
$env:UNITY_PROJECT_PATH='X:\from-process-env'
@'
import unity_session
print(unity_session.resolve_project_path('X:/from-arg'))
'@ | python -
```

Working directory:

```text
F:\C3\unity-puer-exec-workspace\unity-puer-exec\.claude\skills\unity-puer-exec
```

Expected result:

- the resolved path is `X:\from-arg`

### 5. Verify fallback to CWD when both env sources are absent

This validation may use a temporary patched `.env` path in tests or a targeted unit test rather than mutating the real repository file during validation.

Expected result:

- when neither process environment nor `.env` provides `UNITY_PROJECT_PATH`, the code falls back to `Path.cwd()`

### 6. Verify `.env` file strategy

Check all of the following:

- `.env` is ignored by git
- `.env.example` is tracked by git
- runtime loading reads `.env`
- runtime loading does not treat `.env.example` as an active config file

## Acceptance Criteria

This plan is complete only when all of the following are true:

- no third-party Python package is added
- Python entry points can resolve `UNITY_PROJECT_PATH` from repository-local `.env`
- existing process environment variables are not overwritten by `.env`
- `.env` is ignored by git and `.env.example` is tracked
- explicit CLI argument precedence remains unchanged
- unit tests cover `.env` autoload behavior
- repository documentation reflects the new behavior
- after implementation is complete, this temporary plan document is deleted before the final implementation commit

## Commit Plan

After approval, execution will use two commits:

1. commit this plan document
2. implement the changes, validate them, delete this plan document, and commit the final implementation
