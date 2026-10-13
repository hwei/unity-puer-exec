## Why

Stated up front because it decides the shape of both the doc edit and the code fix: **yes,
`AGENTS.md` should formally define `evidence` as multi-valued, and the tooling should treat it that
way everywhere.**

The alternative — declare it single-valued and treat the list form as an accident — contradicts
three shipped archived records, would require rewriting their meaning, and would still leave the
parser accepting lists with no rule saying so. The multi-valued reading matches the field name,
matches `blocked_by` in the same file, and matches the YAML conventions the template invites.

## Context

The repository has two prior governance statements about `evidence`, neither complete:

- `AGENTS.md`: names the four allowed values, silent on cardinality.
- `openspec/changes/archive/2026-10-13-fix-change-meta-evidence-list-parsing/`: fixed the parser,
  explicitly deferred this documentation, and left the filter as a separate follow-up.

The facts that need recording or fixing:

| Fact | Where it lives today |
|---|---|
| Scalar, inline list `[a, b]`, and block list `- a` are all accepted | `tools/openspec_change_meta.py:_normalize_evidence` |
| Several values collapse to one string joined with `", "` | same function |
| `dump_meta` writes the joined string back as a scalar; re-parsing splits it | `dump_meta` + `_normalize_evidence` |
| Ranking uses the strongest (lowest-order) entry; unknown entries rank last | `tools/openspec_backlog.py:evidence_rank` |
| An empty `evidence` is a parse error | `_normalize_evidence` |
| `--evidence` matches by exact whole-string equality | `tools/openspec_backlog.py:filter_records` (defect, fixed here) |
| `--evidence` has no argparse `choices`; any string is accepted | `tools/openspec_backlog.py` argument setup |

The split logic currently exists only inline in `evidence_rank`, which splits on `,` and strips.

## Goals / Non-Goals

**Goals:**

- Make cardinality, input forms, the canonical form, the join format, ranking, and the empty-value
  rule explicit in `AGENTS.md`.
- `--evidence tests` matches any record whose `evidence` includes `tests`, independent of order.
- One shared notion of "the values in an `evidence` string", used by both filter and rank.
- Keep the `AGENTS.md` statement short enough that it reads as convention, not parser documentation.

**Non-Goals:**

- Not describing the parser's internals, error text, or validation order.
- Not adding an "exclude" or repeated `--evidence` flag surface.
- Not adding `choices` to the other filter flags (`--type`, `--priority`, `--assumption-state`,
  `--meta-status`); they are single-valued and out of scope.
- Not changing `ChangeMeta.evidence`, which stays a joined string.
- Not changing ranking results.
- Not rewriting archived records — that is `backfill-legacy-change-meta-records`.

## Decisions

### Decision 1: Declare `evidence` multi-valued, with an empty list invalid

`blocked_by` is a list that may be empty. `evidence` cannot: there is no defensible reading of a
record with no evidence, and the parser already rejects it. Documenting "one or more" rather than
"zero or more" keeps the two list fields from looking interchangeable when they are not.

### Decision 2: Scalar joined form is canonical; list forms are accepted input

The archive is overwhelmingly scalar, and `dump_meta` writes scalar. `AGENTS.md` states that records
should be written as `evidence: tests` or `evidence: tests, manual-check`, and that the parser also
accepts list forms for tolerance. This matches the archive guard added by
`backfill-legacy-change-meta-records`, which rejects list form in archived records — the two changes
state the same rule from opposite ends.

### Decision 3: Record the `", "` join as a defined format, in written order

The prior change flagged the join as a risk: a de facto format that hand-written records drift
toward. Naming it in `AGENTS.md` converts that drift into a documented convention. The order is the
author's written order — not sorted, because sorting would lose the author's emphasis.

### Decision 4: Document ranking as "strongest entry wins", not as an order table

The full ordering lives in `tools/openspec_backlog.py:EVIDENCE_ORDER` and is a ranking heuristic,
not part of the field's meaning. `AGENTS.md` states the rule; the table stays in code.

### Decision 5: One splitter, used by both `filter_records` and `evidence_rank`

Extract `evidence_values(evidence: str) -> tuple[str, ...]` (split on `,`, strip, drop empties —
the exact behavior `evidence_rank` has today). `evidence_rank` calls it; the filter calls it. One
definition of "what values does this string name" is the actual defect being fixed; duplicating the
split would recreate the disagreement. `evidence_values` answers "which values" and `evidence_rank`
answers "how strong" — they are not redundant.

### Decision 6: The flag is an includes-match over a single declared value

Matching becomes `requested in evidence_values(meta.evidence)`. Order becomes irrelevant, and
`--evidence tests` finds `tests, cli-transcript`. An exact-set match was rejected because it
re-creates the original defect; returning a superset of "exactly tests" is the useful direction for
a filter whose purpose is narrowing a work queue.

`--evidence` gains `choices=tuple(EVIDENCE_ORDER)`. Today the flag has no `choices`, so a joined
string like `"tests, cli-transcript"` is accepted and exact-matched by accident. With includes-match
that input would silently match nothing; rejecting it at argparse makes the single-value contract
explicit. Pin the rejection in a test so it is stated, not incidental.

### Decision 7: Unknown values inside a stored `evidence` do not break filtering

A stored record could carry a value that later becomes unrecognized. The filter does not raise; it
simply will not match. `evidence_rank` already degrades unknown entries to last place. Both stay
non-raising so one odd record cannot break `openspec_backlog.py list`.

### Decision 8: Document the fixed behavior directly

Because the filter is fixed in the same change, `AGENTS.md` does not need a "known limitation"
pointer. If the `--evidence` behavior is mentioned at all, it is described as includes-match.

## Risks / Trade-offs

**Documentation drifts from code** → every rule stated in `AGENTS.md` must be pinned by an existing
or added test, so a code change that breaks the doc breaks the suite first.

**A user relying on `--evidence "tests, manual-check"` exact matching loses it** → that was never a
declared value; Decision 6 turns the silent accident into an explicit argparse error.

**Includes-match returns more rows than before** → acceptable for a narrowing filter; pin the exact
expected set in a test so the semantics are visible.

**`AGENTS.md` grows another paragraph** → keep it to the metadata section and put nothing there that
a reader can get from the source. If a rule needs a table, it belongs in code.
