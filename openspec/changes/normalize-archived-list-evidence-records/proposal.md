## Why

`2026-10-13-fix-change-meta-evidence-list-parsing` made the parser accept the list form of
`evidence` and explicitly deferred the question of whether the affected records should be rewritten.
This change answers it: **yes, rewrite them.**

Three archived `meta.yaml` files carry the list form:

| Change | Form |
|---|---|
| `2026-04-01-remove-wait-until-ready-command` | block list (`- tests`, `- manual-check`) |
| `2026-10-13-make-base-url-exec-refresh-recoverable` | inline list (`[tests, host-validation, cli-transcript]`) |
| `2026-10-13-reproduce-play-mode-transport-reset-flake` | block list (`- tests`, `- cli-transcript`, `- host-validation`) |

The case for rewriting, stated in full because the prior change recorded it as open:

- Archived `meta.yaml` files are **inputs to tooling**, not narrative history. `meta.yaml` is
  structured data consumed by `tools/openspec_backlog.py`; the prose is in `proposal.md`. Rewriting a
  data field does not alter what the change said or did.
- The archive is overwhelmingly scalar (120 of 123 parseable records); these three are the
  **outliers**, not the other way round. Restoring the majority form for them is a small correction,
  not a migration. See design.md for the measured distribution.
- The rewrite is currently **cosmetic**: after the parser fix all three parse. So the cost of leaving
  them is a permanently mixed-form archive, and the cost of rewriting them is a three-line diff.

The case against, for completeness: archive immutability is a real convention, and rewriting
history to suit a parser can look like massaging the past. That argument is answered by scope —
this touches only the `evidence` field of three records, preserves each value and its order exactly,
and changes no `change_type`, `priority`, `assumption_state`, or `updated_at`.

## What Changes

- Rewrite the `evidence` field of the three records above from list form to the equivalent scalar
  joined string.
- Tighten the real-archive guard so it no longer needs to tolerate list-form `evidence`.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

(none)

Rewriting archived structured data to a canonical form is a record-hygiene action, not a spec-level
behavior change. `.openspec.yaml` sets `skip_specs: true`.

## Impact

- Affected records: the three `meta.yaml` files listed above.
- Affected test: `tests/test_openspec_change_meta.py`. Its real-archive guard gains an assertion that
  no archived `meta.yaml` uses list-form `evidence`, so the normalized form is enforced going forward.
- No parser, tool, or product behavior changes — the same values are read before and after, because
  the scalar written is exactly the join the parser already computes for the list.
- Ordering note: this should land together with, or after, `define-evidence-as-multi-valued`, since
  that change states the canonical form in `AGENTS.md` and this change applies it to history.