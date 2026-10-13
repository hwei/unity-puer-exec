## Why

Stated up front because it decides the shape of the doc edit: **yes, `AGENTS.md` should formally
define `evidence` as multi-valued.**

The alternative — declare it single-valued and treat the list form as an accident — contradicts
three shipped archived records, would require rewriting them, and would still leave the parser
accepting lists with no rule saying so. The multi-valued reading matches the field name, matches
`blocked_by` in the same file, and matches the YAML conventions the template invites.

## Context

The repository has two prior governance statements about `evidence`, neither complete:

- `AGENTS.md`: names the four allowed values, silent on cardinality.
- `openspec/changes/archive/2026-10-13-fix-change-meta-evidence-list-parsing/`: fixed the parser
  and explicitly deferred this documentation as "a governance edit to fold in deliberately rather
  than an automatic consequence of the fix".

The facts that need recording:

| Fact | Where it lives today |
|---|---|
| Scalar, inline list `[a, b]`, and block list `- a` are all accepted | `tools/openspec_change_meta.py:_normalize_evidence` |
| Several values collapse to one string joined with `", "` | same function |
| `dump_meta` writes the joined string back as a scalar; re-parsing splits it | `dump_meta` + `_normalize_evidence` |
| Ranking uses the strongest (lowest-order) entry | `tools/openspec_backlog.py:evidence_rank` |
| An empty `evidence` is a parse error | `_normalize_evidence` |
| `--evidence` matches by exact string equality | `tools/openspec_backlog.py:filter_records` (defect, tracked separately in `match-evidence-filter-on-multi-value`) |

## Goals / Non-Goals

**Goals:**

- Make cardinality, input forms, the join format, ranking, and the empty-value rule explicit.
- Keep the statement short enough that it reads as convention, not as parser documentation.

**Non-Goals:**

- Not describing the parser's internals, error text, or validation order.
- Not fixing the `--evidence` filter semantics — that is `match-evidence-filter-on-multi-value`.
- Not rewriting archived records — that is `normalize-archived-list-evidence-records`.

## Decisions

### Decision 1: Declare `evidence` multi-valued, with an empty list invalid

`blocked_by` is a list that may be empty. `evidence` cannot: there is no defensible reading of a
record with no evidence, and the parser already rejects it. Documenting "one or more" rather than
"zero or more" keeps the two list fields from looking interchangeable when they are not.

### Decision 2: Record the `", "` join as a defined format, not an implementation detail

`2026-10-13-fix-change-meta-evidence-list-parsing` flagged the join as a risk: it becomes a de
facto format that hand-written records drift toward. Naming it in `AGENTS.md` converts that drift
from accident into a documented convention. The order is the author's written order — it is not
sorted, because sorting would lose the author's emphasis.

### Decision 3: Document ranking as "strongest entry wins", not as an order table

The full `tests` < `host-validation` < `cli-transcript` < `manual-check` ordering lives in
`tools/openspec_backlog.py:EVIDENCE_ORDER` and is a ranking heuristic, not part of the field's
meaning. `AGENTS.md` states the rule; the table stays in code where it is used.

### Decision 4: Cross-reference the exact-match filter limitation rather than documenting it as intended

The `--evidence` flag compares the whole joined string, so `--evidence tests` misses
`"tests, cli-transcript"`. Writing that down as intended behavior would ratify a defect. The
`AGENTS.md` note points at `match-evidence-filter-on-multi-value` instead.

## Risks / Trade-offs

**Documentation drifts from code** → the doc states rules the tests in
`tests/test_openspec_change_meta.py` already pin (join format, empty-value rejection, accepted
forms), so a code change that breaks the doc breaks the suite first.

**`AGENTS.md` grows another paragraph** → keep it to the metadata section, and put nothing there
that a reader can get from the source. If a rule needs a table, it belongs in code.