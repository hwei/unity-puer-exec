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
- `.tmp/` is the repository-local location for transient validation probes and scratch scripts and is kept out of normal version control.

## Working Agreement

- OpenSpec is the canonical governance and planning system for this repository.
- Use `openspec/project.md` for repository-wide context and collaboration rules.
- Use `openspec/specs/` for durable requirements that should survive individual changes.
- Use `openspec/changes/` for scoped change work. Proposal, specs, and tasks are the default minimum before substantial implementation.
- Treat non-archived OpenSpec changes as the repository planning surface.
- Treat backlog specifically as the subset of non-archived changes that the repository-local backlog tooling currently marks eligible for recommendation.
- Treat temporary execution context as ephemeral. Distill stable conclusions into `openspec/specs/`, source, tests, or concise repository guidance rather than keeping long-lived plan prose.
- The working tree does not keep a parallel legacy `docs/` workflow entry path.
- When a follow-up change depends on earlier validation or archived findings, proposal and design artifacts should name the upstream change and summarize the inherited finding that justifies the new scope.
- For propose/apply/archive work, prefer the installed OpenSpec skills first and the official `openspec` CLI as the direct fallback path.

## Agent Conventions

- Prefer reading only the minimal OpenSpec artifacts needed for the current task.
- When a change affects behavior or workflow materially, create or continue an OpenSpec change instead of editing long-lived truth directly without change context.
- Maintain repository-owned change metadata in `meta.yaml` for every non-archived change. The current convention is `status`, `change_type`, `priority`, `blocked_by`, `assumption_state`, `evidence`, and `updated_at`.
- Treat `meta.yaml` as machine-readable planning metadata only. Repository backlog recommendation is derived from repository facts and metadata together rather than from `status` alone.
- When new work is discovered during execution, classify it as in-scope, prerequisite, or adjacent before continuing implementation.
- When starting work from a clean tree, consult the backlog tooling rather than guessing from prose alone.
- When apply work ends, always produce an explicit closeout finding summary stating whether new follow-up candidates were discovered.
- If follow-up candidates are discovered during closeout, classify them as `product-improvement`, `workflow-improvement`, `tooling-improvement`, or `validation-gap`, and discuss them with the human before promoting them into further work.
- When a change is ready to close, recommend whether to run `git commit`, `openspec archive`, and the final `git commit`, but leave execution to the human unless explicitly asked.
- Do not manually move or recreate `openspec/changes/` directory entries during normal propose/apply/archive workflow. Reserve manual directory edits for explicit repair of abnormal repository state.
- Once a change is archived, clean up stale active-directory placeholders so archived work does not continue to appear as an active planning entry.
- Keep product behavior in code and tests, and keep durable contract statements in OpenSpec specs. Do not use stale prose as authoritative when code and tests disagree.
- Prefer `.tmp/` over the repository root for local validation probes and other short-lived scratch artifacts.

## Change Type Policy

- `feature`: proposal, tasks, and durable specs are expected; add design when architecture changes materially.
- `harness`: proposal and tasks are expected; add design in most cases; add durable specs when contracts or workflow rules change.
- `validation`: proposal and tasks are expected; add design only when coordination or setup is non-trivial; add durable specs only when validation policy becomes long-lived truth.
- `refactor`: proposal and tasks are expected; add design when risk or coordination is significant; add durable specs only when external behavior or governance changes.
- `spike`: keep proposal lightweight and tasks explicit; add design only when it helps reasoning; add durable specs only if the spike graduates into stable requirements.

## Repository Layout

- `openspec/project.md`: repository-wide context and collaboration guidance
- `openspec/specs/`: durable capability requirements
- `openspec/changes/`: active and archived change proposals
- `openspec/templates/change-meta.yaml`: repository-owned metadata template for non-archived changes
- `packages/com.txcombo.unity-puer-exec/`: formal Unity package home
- `cli/python/`: repo-owned Python CLI baseline
- `tools/new_openspec_change.py`: helper that creates a new OpenSpec change and seeds `meta.yaml`
- `tools/openspec_backlog.py`: filter and rank non-archived changes from `meta.yaml`
- `tools/prepare_validation_host.py`: validation-host wiring helper
- `tests/`: canonical repository-level tests
