## Why

The archive's `meta.yaml` records are inputs to tooling (`tools/openspec_backlog.py`), and two
independent hygiene problems keep the archive guard from meaning "every archived record is
well-formed":

**1. Missing records and missing fields.** One test constant is the only thing keeping the archive
guard green:

```python
KNOWN_LEGACY_ARCHIVE_RECORDS = frozenset({...})  # tests/test_openspec_change_meta.py
```

That constant was introduced by `2026-10-13-fix-change-meta-evidence-list-parsing` as an explicit
scope boundary: those records fail for a reason unrelated to the parser fix, so tolerate them by
name rather than block on them. The boundary was drawn correctly. But a name-based exemption is a
permanent hole that only widens, and the failure it hides is not historical trivia — it is "this
repository cannot parse all of its own change records."

Measured across `openspec/changes/archive/` when this change was proposed:

| Gap | Count | Records |
|---|---|---|
| No `meta.yaml` file at all | 10 | `2026-03-17-add-apply-closeout-governance`, `2026-03-17-archive-legacy-decisions`, `2026-03-17-delete-legacy-docs`, `2026-03-17-migrate-legacy-governance-to-openspec`, `2026-03-25-add-log-brief-capability`, `2026-03-26-add-exec-script-args`, `2026-03-26-expand-next-step-guidance`, `2026-03-26-surface-ctx-contract-in-exec-help`, `2026-05-11-improve-cache-staleness-detection-and-examples`, `2026-05-12-include-readme-in-upm-package` |
| `meta.yaml` missing `blocked_by` | 3 | `2026-03-26-exec-import-support`, `2026-03-26-readme-user-facing-rewrite`, `2026-05-12-exec-async-warning-status` |
| `meta.yaml` missing `evidence` | 1 | `2026-05-14-relax-runtime-guidance-compile-count-situation` |

Only the last 4 are in `KNOWN_LEGACY_ARCHIVE_RECORDS`. The 10 directories with no `meta.yaml` are
not covered by the guard at all, because the guard globs `*/meta.yaml` and a missing file is not a
parse failure — it is invisible.

**2. Three records use list-form `evidence`.** `2026-10-13-fix-change-meta-evidence-list-parsing`
made the parser accept list-form `evidence` and deferred whether those records should be rewritten.
This change answers it: **yes, rewrite them** to the scalar joined form.

| Change | Form |
|---|---|
| `2026-04-01-remove-wait-until-ready-command` | block list (`- tests`, `- manual-check`) |
| `2026-10-13-make-base-url-exec-refresh-recoverable` | inline list (`[tests, host-validation, cli-transcript]`) |
| `2026-10-13-reproduce-play-mode-transport-reset-flake` | block list (`- tests`, `- cli-transcript`, `- host-validation`) |

The archive is overwhelmingly scalar (120 of 123 parseable records at proposal time); these three
are outliers. Rewriting is cosmetic for the parser (all three already parse) but removes a
permanently mixed-form archive at the cost of a three-line diff. Archive immutability is answered by
scope: only the `evidence` line changes, values and order are preserved exactly.

Both problems edit the same archived `meta.yaml` set and the same real-archive guard, so they are
done in one change. Splitting them produced contradictory ordering (each half required the other to
land first) and conflicting tasks on `KNOWN_LEGACY_ARCHIVE_RECORDS`. This change absorbs the
superseded `normalize-archived-list-evidence-records`.

## What Changes

- Rewrite the `evidence` field of the three list-form records to the equivalent scalar joined
  string (`", "`, written order).
- Backfill `meta.yaml` for the 10 archived directories that have none, writing `evidence` in scalar
  form.
- Backfill the missing `blocked_by` / `evidence` fields on the 4 that have a partial file.
- Delete `KNOWN_LEGACY_ARCHIVE_RECORDS` so the archive guard asserts that every archived record
  parses, with no exemptions.
- Add guard assertions that every archived directory has a `meta.yaml`, and that no archived
  `meta.yaml` uses list-form `evidence`.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

(none)

This is record hygiene plus a repository-local test guard. No capability behavior changes, and the
parser keeps accepting list form. `.openspec.yaml` sets `skip_specs: true`.

## Impact

- Affected records: 17 archived directories (3 rewritten, 10 created, 4 completed), plus the
  real-archive guard in `tests/test_openspec_change_meta.py`.
- No parser, tool, or product behavior changes — rewritten records read back as identical values.
- Affected tooling: `openspec_backlog.py` can resolve dependencies among archived records once
  `blocked_by` exists everywhere.
- Ordering: independent of `define-evidence-as-multi-valued`. That change documents scalar as the
  canonical `evidence` form; this change applies it to history. Either may land first.
