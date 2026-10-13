## Why

`AGENTS.md` lists the allowed `evidence` values but does not say whether a single change record
may name more than one:

```
- Allowed `evidence` values: `tests`, `host-validation`, `cli-transcript`, and `manual-check`.
```

As of `2026-10-13-fix-change-meta-evidence-list-parsing`, the code no longer agrees with that
silence in one direction and disagrees with it in another:

- `tools/openspec_change_meta.py` accepts scalar, inline-list, and block-list `evidence`, and
  collapses several values into one display string joined with `", "`.
- `tools/openspec_backlog.py:evidence_rank` ranks such a string by its strongest entry.
- Three archived records already carry the list form, so the multi-value shape is real history,
  not a hypothetical.
- Nothing documents the collapse format, the ranking rule, or whether a new record *should* name
  one value or several.

Left undocumented, the next author re-derives this by reading source, and the `"tests, cli-transcript"`
string becomes an accidental de facto format that nobody agreed to.

## What Changes

- State in `AGENTS.md` that `evidence` is multi-valued.
- State the accepted input forms, the `", "` collapse format, and the ranking rule.
- State whether the collapse is stable enough to be relied on by tooling.

This is a documentation change to an existing convention. It edits no behavior.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

(none)

`AGENTS.md` is repository convention, not an `openspec/specs/` capability, so this records a
governance decision without creating a delta spec. `.openspec.yaml` sets `skip_specs: true`.

## Impact

- Affected file: `AGENTS.md` (Change metadata section).
- No code, test, or record changes.
- Downstream readers: `tools/openspec_backlog.py` and `tools/new_openspec_change.py`, whose
  behavior stays as-is and becomes documented.