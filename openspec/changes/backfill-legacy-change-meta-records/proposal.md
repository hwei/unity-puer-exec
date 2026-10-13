## Why

14 archived change directories are missing required `meta.yaml` fields, and one test constant is
currently the only thing keeping the archive guard green:

```python
KNOWN_LEGACY_ARCHIVE_RECORDS = frozenset({...})  # tests/test_openspec_change_meta.py
```

That constant was introduced by `2026-10-13-fix-change-meta-evidence-list-parsing` as an explicit
scope boundary: those records fail for a reason unrelated to the parser fix, so tolerate them by
name rather than block on them. The boundary was drawn correctly. But a name-based exemption is a
permanent hole that only widens, and the failure it hides is not historical trivia — it is "this
repository cannot parse all of its own change records."

Measured across `openspec/changes/archive/` (134 directories):

| Gap | Count | Records |
|---|---|---|
| No `meta.yaml` file at all | 10 | `2026-03-17-add-apply-closeout-governance`, `2026-03-17-archive-legacy-decisions`, `2026-03-17-delete-legacy-docs`, `2026-03-17-migrate-legacy-governance-to-openspec`, `2026-03-25-add-log-brief-capability`, `2026-03-26-add-exec-script-args`, `2026-03-26-expand-next-step-guidance`, `2026-03-26-surface-ctx-contract-in-exec-help`, `2026-05-11-improve-cache-staleness-detection-and-examples`, `2026-05-12-include-readme-in-upm-package` |
| `meta.yaml` missing `blocked_by` | 3 | `2026-03-26-exec-import-support`, `2026-03-26-readme-user-facing-rewrite`, `2026-05-12-exec-async-warning-status` |
| `meta.yaml` missing `evidence` | 1 | `2026-05-14-relax-runtime-guidance-compile-count-situation` |

Only the last 4 are in `KNOWN_LEGACY_ARCHIVE_RECORDS`. The 10 directories with no `meta.yaml` are
not covered by the guard at all, because the guard globs `*/meta.yaml` and a missing file is not a
parse failure — it is invisible.

## What Changes

- Backfill `meta.yaml` for the 10 archived directories that have none.
- Backfill the missing `blocked_by` / `evidence` fields on the 4 that have a partial file.
- Delete `KNOWN_LEGACY_ARCHIVE_RECORDS` so the archive guard asserts that every archived record
  parses, with no exemptions.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

(none)

This completes the metadata set `AGENTS.md` already mandates. No capability behavior changes.
`.openspec.yaml` sets `skip_specs: true`.

## Impact

- Affected records: 14 archived directories, plus the real-archive guard in
  `tests/test_openspec_change_meta.py`.
- Affected tooling: `openspec_backlog.py` can begin resolving dependencies among archived records
  once `blocked_by` exists, which is what makes `2026-03-26-*` dependency data usable.
- Ordering: should land **after** `normalize-archived-list-evidence-records`, so that change's
  canonical-`evidence` assertion is not immediately contradicted by newly written files.