> **Superseded** by `define-evidence-as-multi-valued` (2026-10-13), which absorbs this change's scope and tasks so the
> ordering and guard edits stay consistent. Archive this change without applying it.

## Why

`openspec_backlog.py --evidence` compares the whole stored string:

```python
if evidence and meta.evidence != evidence:
    continue
```

`evidence` is now a possibly joined string, because
`2026-10-13-fix-change-meta-evidence-list-parsing` made the parser accept multiple values and
collapse them with `", "`. So the filter no longer means what its flag name promises:

| Stored `evidence` | `--evidence tests` | `--evidence "tests, cli-transcript"` |
|---|---|---|
| `tests` | match | no match |
| `tests, cli-transcript` | **no match** | match |
| `cli-transcript, tests` | **no match** | no match (order-sensitive) |

Three distinct problems in one comparison: a record naming `tests` among other evidence is invisible
to `--evidence tests`; the match is order-sensitive, so the same set of values in a different order
misses; and the user must type the join separator to match a joined record at all.

This was unreachable while `evidence` was effectively single-valued — which is why
`2026-10-13-fix-change-meta-evidence-list-parsing` made fixing the filter a separate follow-up
rather than part of the parser fix. Fixing the parser without the filter is what made this reachable.

## What Changes

- Match `--evidence` against the parsed set of evidence values, so a record matches if the requested
  value is one of the values it names.
- Keep the flag single-valued: it selects records that *include* a given evidence value.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

(none)

This corrects repository-local CLI filter semantics. `openspec_backlog.py` is tooling, not a
capability in `openspec/specs/`. `.openspec.yaml` sets `skip_specs: true`.

## Impact

- Affected code: `tools/openspec_backlog.py` — `filter_records`, and possibly the `--evidence` help
  text and the existing `evidence` parser for values.
- Affected tests: `tests/test_openspec_backlog.py`.
- Interaction with `evidence_rank`: ranking already splits the joined string via
  `evidence_rank`. This change makes the filter consistent with that, so the two halves of the tool
  stop disagreeing about what a joined value means.
- Interaction with `define-evidence-as-multi-valued`: that change documents the filter's exact-match
  behavior and points here. This change makes that pointer stale, so the two should land together or
  `define-evidence-as-multi-valued` should follow this one.
- Interaction with `normalize-archived-list-evidence-records`: that change rewrites the three
  archived records to scalar. This change only affects filtering, and the default suite filters
  non-archived changes, so neither blocks the other.