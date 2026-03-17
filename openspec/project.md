# Project Context

## Repository Identity

- This repository is the product source of truth for the formal Unity package `com.txcombo.unity-puer-exec` and the formal CLI `unity-puer-exec`.
- The validation host project lives outside this repository. It exists to exercise the product against a real Unity project and is not the product source of truth.
- Product-facing durable requirements live in `openspec/specs/`.
- Active work is captured as OpenSpec changes under `openspec/changes/`.

## Environment

- Repository Python entry points auto-load `./.env` when needed.
- If `UNITY_PROJECT_PATH` is present in the process environment, it overrides `./.env`.
- `UNITY_PROJECT_PATH` points to the validation host Unity project.
- This repository does not assume a repository-local `Project/` directory.
- `./.env` is local-only and must not be committed; `./.env.example` is the tracked template.

## Working Agreement

- OpenSpec is the canonical governance and planning system for this repository.
- Use `openspec/project.md` for repository-wide context and collaboration rules.
- Use `openspec/specs/` for durable requirements that should survive individual changes.
- Use `openspec/changes/` for scoped change work. Proposal, specs, and tasks are the default minimum before substantial implementation.
- Treat temporary execution context as ephemeral. Distill stable conclusions into `openspec/specs/`, source, tests, or concise repository guidance rather than keeping long-lived plan prose.

## Agent Conventions

- Prefer reading only the minimal OpenSpec artifacts needed for the current task.
- When a change affects behavior or workflow materially, create or continue an OpenSpec change instead of editing long-lived truth directly without change context.
- Keep product behavior in code and tests, and keep durable contract statements in OpenSpec specs. Do not use stale prose as authoritative when code and tests disagree.
- Legacy `docs/` files are transitional references only unless a file explicitly says otherwise.

## Repository Layout

- `openspec/project.md`: repository-wide context and collaboration guidance
- `openspec/specs/`: durable capability requirements
- `openspec/changes/`: active and archived change proposals
- `packages/com.txcombo.unity-puer-exec/`: formal Unity package home
- `cli/python/`: repo-owned Python CLI baseline
- `tools/prepare_validation_host.py`: validation-host wiring helper
- `tests/`: canonical repository-level tests
