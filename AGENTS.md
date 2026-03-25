## Environment setup

- Repository Python entry points auto-load `./.env` when needed.
- If you set `UNITY_PROJECT_PATH` in the process environment explicitly, that value overrides `./.env`.
- `UNITY_PROJECT_PATH` points to the validation host Unity project.
- This repository does not assume a repository-local `Project/` directory.
- `./.env` is local-only and should not be committed; use `./.env.example` as the tracked template.

## OpenSpec entry points

- `openspec/config.yaml` carries repository-wide context for OpenSpec workflows.
- `openspec/specs/` holds durable requirements that survive individual changes.
- `openspec/changes/` holds active and archived change artifacts.
- `tests/` is the canonical repository-level test location.
- `.tmp/` is the preferred local-only location for transient validation probes and scratch scripts.
- Use OpenSpec artifacts directly; there is no parallel `docs/` workflow surface in the working tree.
- For propose/apply/archive operations, prefer the installed OpenSpec skills first. Use the official `openspec` CLI when a direct command path is needed.

## Change metadata

- Every non-archived OpenSpec change should carry a repository-owned `meta.yaml`.
- `meta.yaml` currently tracks optional explicit `status` disposition, `change_type`, `priority`, `blocked_by`, `assumption_state`, `evidence`, and `updated_at`.
- Allowed explicit `status` values for new work: `blocked`, `superseded`.
- Legacy non-archived changes may still carry `queued` or `active` during migration; treat those as compatibility values rather than the normal repository planning model.
- Allowed `change_type` values: `feature`, `harness`, `validation`, `refactor`, `spike`.
- Allowed `priority` values: `P0`, `P1`, `P2`.
- `blocked_by` is a one-way list of prerequisite change names. Do not maintain reciprocal `unblocks` fields.
- Allowed `assumption_state` values: `valid`, `needs-review`, `invalid`.
- Allowed `evidence` values: `tests`, `host-validation`, `cli-transcript`, `manual-check`.
- `updated_at` uses `YYYY-MM-DD`.
- Backlog is the subset of non-archived changes that repository-local tooling derives as `eligible`.
- Explicit `status=blocked` means the change is not currently actionable even if dependency checks alone would not detect that.
- Explicit `status=superseded` means the change was replaced and is awaiting archive.
- Prefer `python tools/new_openspec_change.py <change-name>` when creating a new change so `meta.yaml` is seeded automatically.
- Prefer `openspec archive <change-name>` when archiving a completed change. Do not manually move `openspec/changes/` directories during normal workflow.
- Before selecting fresh work from a clean tree, consult the backlog tooling instead of guessing from prose alone.
- Use `python tools/openspec_backlog.py next` for the default ranked recommendation, or `python tools/openspec_backlog.py list --backlog` to inspect the recommendable backlog explicitly.

## Change type policy

- `feature`: proposal, tasks, and durable specs are expected; add design when architecture changes materially.
- `harness`: proposal and tasks are expected; add design in most cases; add durable specs when contracts or workflow rules change.
- `validation`: proposal and tasks are expected; add design only when coordination or setup is non-trivial; add durable specs only when validation policy becomes long-lived truth.
- `refactor`: proposal and tasks are expected; add design when risk or coordination is significant; add durable specs only when external behavior or governance changes.
- `spike`: keep proposal lightweight and tasks explicit; add design only when it helps reasoning; add durable specs only if the spike graduates into stable requirements.

## Apply checkpoints

- Before starting apply work, inspect `git status`.
- If the working tree contains unrelated or risky in-progress edits, prefer creating a commit checkpoint before continuing.
- A clean tree is preferred for apply work, but git commits are an execution habit rather than a hard OpenSpec workflow gate.
- Place ad hoc validation probes and short-lived scratch scripts under `.tmp/` instead of the repository root.

## Apply closeout

- Every apply session should end with an explicit closeout finding summary.
- The summary must say either `No new follow-up work identified` or `New follow-up candidates identified`.
- Allowed follow-up categories are `product-improvement`, `workflow-improvement`, `tooling-improvement`, and `validation-gap`.
- Follow [apply-closeout-review spec](../openspec/specs/apply-closeout-review/spec.md) for human-discussion requirements on new follow-up candidates.
- When the change state is ready to close, recommend whether to run `git commit`, `openspec archive`, and the final `git commit`.
- Do not execute the closeout sequence automatically unless the human explicitly asks for it.
