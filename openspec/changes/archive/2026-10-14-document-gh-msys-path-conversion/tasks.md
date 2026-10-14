# Tasks

## 1. Document the git-bash path-conversion convention

- [x] 1.1 Add a short Windows git-bash section to `AGENTS.md` stating that native Windows tools such as `gh` must run with `MSYS_NO_PATHCONV=1` when arguments or emitted values contain `/`-joined text, with the `completedC:/Program Files/Git/success` example. Verify: `git diff` touches only `AGENTS.md`.

## 2. Validation and Closeout

- [x] 2.1 Reproduce the mangling and confirm the documented fix. Verify: `gh run view <run-id> --json status,conclusion --jq '.status+"/"+.conclusion'` prints a mangled value without the variable and `completed/success` with `MSYS_NO_PATHCONV=1`.
- [x] 2.2 Run strict validation. Verify: `openspec validate document-gh-msys-path-conversion --strict` passes with `skip_specs: true`.
- [x] 2.3 Complete the required apply closeout review and record the finding with allowed categories.

## Workflow follow-up

- Archive the change after the project's review requirements are satisfied.
