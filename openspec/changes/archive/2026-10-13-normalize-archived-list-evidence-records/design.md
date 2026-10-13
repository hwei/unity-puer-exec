## Context

The archive contains 134 change directories. Their `meta.yaml` shapes:

| Shape | Count |
|---|---|
| Scalar `evidence: <value>` | 120 |
| List form (`evidence:` + `- item`, or `evidence: [a, b]`) | 3 |
| No `meta.yaml` file at all | 10 |
| `meta.yaml` present but missing the `evidence` line entirely | 1 (`2026-05-14-relax-runtime-guidance-compile-count-situation`) |

The 120-vs-3 split is the decisive fact. Scalar is overwhelmingly the established form in this
repository's own history; the three list-form records are the outliers, not the other way round.
`2026-10-13-fix-change-meta-evidence-list-parsing` offered "rewrite the outliers to match the
majority" as the pro-rewrite argument and left it undecided.

That framing needs correcting before it is acted on. It is not "canonicalize the multi-value
records" — it is "restore the majority form for the three records that deviated". The proposal's
wording implies the archive is mostly list-form and being corrected; the archive is the opposite.

## Goals / Non-Goals

**Goals:**

- Rewrite exactly three records' `evidence` field to the scalar joined form.
- Preserve each record's values, their order, and every other field byte-for-byte.
- Leave the guard in `tests/test_openspec_change_meta.py` able to detect a *new* list-form record.

**Non-Goals:**

- Not adding the 10 missing `meta.yaml` files. That is `backfill-legacy-change-meta-records`.
- Not touching the record missing the `evidence` line; same reason.
- Not changing the parser, which must keep accepting list form regardless — see Decision 2.
- Not reordering values alphabetically. Written order carries the author's emphasis.

## Decisions

### Decision 1: Rewrite the three records to scalar, preserving order

`evidence: tests, manual-check` is the joined form the parser already produces for a list input.
So rewriting is not a lossy reinterpretation — it is exactly what the tooling produces when it
reads the list form today, written back out. Values and order carry over unchanged.

### Decision 2: Keep parser support for list form; do not "clean up" the parser

The temptation after normalizing the archive is to remove list-form acceptance so the form can
never reappear. Rejected: `2026-10-13-fix-change-meta-evidence-list-parsing` exists precisely
because a parser that rejects valid-looking YAML fails on records nobody can see. Removing the
support re-creates that failure mode for the next hand-written list. Normalizing history does not
justify making history's mistake unrepresentable.

### Decision 3: Detect the regression with a guard, not with a git hook

Add an assertion to the existing real-archive guard that no `meta.yaml` under
`openspec/changes/archive/*/` uses list-form `evidence`. This keeps the canonical-form rule
enforced going forward without adding a commit-time hook, which would be the first such hook in
the repository.

The guard inspects raw text rather than parsed `ChangeMeta`, because parsing deliberately accepts
list form and therefore cannot distinguish the two shapes.

### Decision 4: Do not restyle the whole archive

Only the `evidence` line changes in each of the three records. Comments, key order, quoting style,
and blank lines stay as they are. A normalization pass that also reformats is how an archive stops
being trustworthy as a record.

## Risks / Trade-offs

**Rewriting archived history is itself a judgment call** → bounded by Decision 4 and by preserving
every value; the diff is three `evidence` lines and is reviewable as such.

**A future author writes a list again** → Decision 3's guard fails it in the default suite.

**Scalar and list form parse to the same value, so a mixed archive is invisible** → that
invisibility is exactly why Decision 3 inspects raw text rather than trusting the parse.