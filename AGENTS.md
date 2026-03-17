## Environment setup

- Repository Python entry points auto-load `./.env` when needed.
- If you set `UNITY_PROJECT_PATH` in the process environment explicitly, that value overrides `./.env`.
- `UNITY_PROJECT_PATH` points to the validation host Unity project.
- This repository does not assume a repository-local `Project/` directory.
- `./.env` is local-only and should not be committed; use `./.env.example` as the tracked template.

## OpenSpec entry points

- `openspec/project.md` is the canonical repository-wide context file.
- `openspec/specs/` holds durable requirements that survive individual changes.
- `openspec/changes/` holds active and archived change artifacts.
- `tests/` is the canonical repository-level test location.
- Use OpenSpec artifacts directly; there is no parallel `docs/` workflow surface in the working tree.

## Apply checkpoints

- Before starting apply work, inspect `git status`.
- If the working tree contains unrelated or risky in-progress edits, prefer creating a commit checkpoint before continuing.
- A clean tree is preferred for apply work, but git commits are an execution habit rather than a hard OpenSpec workflow gate.
