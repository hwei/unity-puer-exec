## Context

The string-splitting logic for a joined `evidence` value now exists in one place:

```python
def evidence_rank(value: str) -> int:
    parts = [part.strip() for part in value.split(",") if part.strip()]
```

That was introduced for ranking, where splitting was required. `filter_records` was left comparing
whole strings, so the tool now splits the field in one place and treats it as opaque in another.
`openspec_backlog.py list --evidence tests` currently hides a change whose `evidence` is
`tests, cli-transcript` — the record most likely to be the one the user is looking for.

Two adjacent facts constrain the design:

- `EVIDENCE_ORDER` in `openspec_backlog.py` is the authority on the value set and is also the
  argparse `choices` source for `--evidence`. So the flag already rejects unknown single values; it
  does not need new validation, only new matching.
- `--evidence` currently accepts a joined string by accident (because `!=` on the raw value
  happens to match when the user types the same join). That accident is not worth preserving, but
  silently breaking it is also worth avoiding; see Decision 2.

## Goals / Non-Goals

**Goals:**

- `--evidence tests` matches any record whose `evidence` includes `tests`.
- Match independent of value order.
- One shared notion of "the values in an `evidence` string", used by both filter and rank.

**Non-Goals:**

- Not adding an "exclude this evidence" or multi-value (`--evidence tests --evidence cli-transcript`)
  flag surface. Not asked for; do not widen the CLI.
- Not changing `ChangeMeta.evidence`, which stays a joined string per
  `2026-10-13-fix-change-meta-evidence-list-parsing` Decision 1.
- Not changing ranking.

## Decisions

### Decision 1: Introduce one splitter and use it in both `filter_records` and `evidence_rank`

`evidence_rank` already contains the split logic inline. Extract it to a single
`evidence_values(evidence: str) -> tuple[str, ...]` helper, have `evidence_rank` call it, and have
the filter call it too. One definition of "what values does this string name" is the actual defect
being fixed; duplicating the split in a second place would recreate the disagreement.

### Decision 2: Interpret the flag as "includes", and reject a joined value the user typed

Matching becomes `requested in evidence_values(meta.evidence)`. This makes order irrelevant and makes
`--evidence tests` find `tests, cli-transcript`.

It also means `--evidence "tests, cli-transcript"` no longer matches that record — the flag is
single-valued, and a joined string is not a value. The existing argparse `choices` already rejects
`"tests, cli-transcript"` as an unknown value, so this behavior is consistent with the flag's
declared contract rather than a new restriction. Pin the rejection in a test so it is stated, not
incidental.

### Decision 3: Keep the filter an "includes" match, not an exact-set match

An exact-set match would make `--evidence tests` miss `tests, cli-transcript` again — the original
defect. An includes-match means the user asks "show me changes whose evidence includes tests", which
is the question the flag name implies. The consequence to accept: `--evidence tests` returns a
superset of "exactly tests". That is the useful direction for a filter whose purpose is narrowing a
work queue.

### Decision 4: Unknown values inside a stored `evidence` string do not block filtering

A record could carry a value that later becomes unrecognized. The filter should not raise on it; it
simply will not match an `--evidence` argument naming that value, and `evidence_rank` already
degrades unknown entries to last place rather than raising. Keep both sides non-raising so one odd
archived record cannot break `openspec_backlog.py list`.

### Decision 5: Update the help text and the `define-evidence-as-multi-valued` pointer

`--evidence` help currently says `Filter by evidence target.`, which does not describe includes-match.
Update it to say the record must *include* the value. And because
`define-evidence-as-multi-valued` documents the exact-match limitation and points here, that pointer
must be corrected when this change lands — otherwise `AGENTS.md` will document a behavior that no
longer exists.

## Risks / Trade-offs

**A user relying on `--evidence "tests, manual-check"` exact matching loses it** → the value was
never a declared `choices` entry, so it was always an accident of string comparison. Decision 2
records the rejection explicitly so it is a stated decision rather than a silent regression.

**Includes-match returns more rows than before** → acceptable for a narrowing filter; pin the exact
expected set in a test so the semantics are visible.

**Two helpers where one would do** → `evidence_values` and `evidence_rank` are not redundant; the
first answers "which values", the second "how strong". Merging them would force ranking concerns into
callers that only want the values.