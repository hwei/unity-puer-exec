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

## Change metadata

- Every non-archived OpenSpec change should carry a repository-owned `meta.yaml`.
- `meta.yaml` currently tracks `status`, `change_type`, `priority`, `blocked_by`, `assumption_state`, `evidence`, and `updated_at`.
- Allowed `status` values: `queued`, `active`, `blocked`, `superseded`.
- Allowed `change_type` values: `feature`, `harness`, `validation`, `refactor`, `spike`.
- Allowed `priority` values: `P0`, `P1`, `P2`.
- `blocked_by` is a one-way list of prerequisite change names. Do not maintain reciprocal `unblocks` fields.
- Allowed `assumption_state` values: `valid`, `needs-review`, `invalid`.
- Allowed `evidence` values: `tests`, `host-validation`, `cli-transcript`, `manual-check`.
- `updated_at` uses `YYYY-MM-DD`.
- `status=queued` is the backlog definition. `active` means in progress. `blocked` means not currently actionable. `superseded` means replaced and awaiting archive.
- Prefer `python tools/new_openspec_change.py <change-name>` when creating a new change so `meta.yaml` is seeded automatically.
- Before selecting fresh work from a clean tree, consult the backlog tooling instead of guessing from prose alone.
- Use `python tools/openspec_backlog.py next` for the default ranked recommendation, or `python tools/openspec_backlog.py list --status queued` to inspect backlog explicitly.

## Apply checkpoints

- Before starting apply work, inspect `git status`.
- If the working tree contains unrelated or risky in-progress edits, prefer creating a commit checkpoint before continuing.
- A clean tree is preferred for apply work, but git commits are an execution habit rather than a hard OpenSpec workflow gate.
