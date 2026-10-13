## Why

`AGENTS.md` lists the allowed `evidence` values but does not say whether a single change record
may name more than one:

```
- Allowed `evidence` values: `tests`, `host-validation`, `cli-transcript`, `manual-check`.
```

As of `2026-10-13-fix-change-meta-evidence-list-parsing`, the tooling treats `evidence` as
multi-valued in some places and single-valued in others:

- `tools/openspec_change_meta.py` accepts scalar, inline-list, and block-list `evidence`, and
  collapses several values into one display string joined with `", "`.
- `tools/openspec_backlog.py:evidence_rank` splits that string and ranks by its strongest entry.
- `tools/openspec_backlog.py:filter_records` compares the **whole** string:

  ```python
  if evidence and meta.evidence != evidence:
      continue
  ```

  So `--evidence` no longer means what its flag name promises:

  | Stored `evidence` | `--evidence tests` | `--evidence "tests, cli-transcript"` |
  |---|---|---|
  | `tests` | match | no match |
  | `tests, cli-transcript` | **no match** | match |
  | `cli-transcript, tests` | **no match** | no match (order-sensitive) |

- Nothing documents the collapse format, the ranking rule, which input form is canonical, or
  whether a new record *should* name one value or several.

Defining the field and fixing the filter are one decision: documenting multi-valued `evidence`
while the filter treats it as opaque would either ratify a defect or require a temporary "known
limitation" note that the fix immediately deletes. This change absorbs the superseded
`match-evidence-filter-on-multi-value`.

## What Changes

- State in `AGENTS.md` that `evidence` is multi-valued (one or more values), the accepted input
  forms, that the scalar joined form (`", "`, written order) is canonical, and the ranking rule.
- Make `openspec_backlog.py --evidence` an includes-match: a record matches if the requested value
  is one of the values it names, independent of order.
- Restrict `--evidence` to the known single values via argparse `choices`, so a joined value is
  rejected rather than accidentally string-matched.
- Extract one shared splitter used by both filtering and ranking.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

(none)

`AGENTS.md` is repository convention and `openspec_backlog.py` is repository-local tooling; neither
is an `openspec/specs/` capability. `.openspec.yaml` sets `skip_specs: true`.

## Impact

- Affected files: `AGENTS.md` (Change metadata section), `tools/openspec_backlog.py`
  (`evidence_rank`, `filter_records`, `--evidence` argument), `tests/test_openspec_backlog.py`,
  and possibly `tests/test_openspec_change_meta.py` for pinning documented rules.
- CLI behavior change: `--evidence tests` returns a superset of today's result;
  `--evidence "tests, cli-transcript"` now errors instead of exact-matching.
- No record changes. Independent of `backfill-legacy-change-meta-records`, which applies the
  canonical scalar form to archived records; either may land first.
