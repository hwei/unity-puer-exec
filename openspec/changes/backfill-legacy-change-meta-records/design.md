## Context

The archive's `meta.yaml` records have two kinds of defect, measured when this change was proposed
(138 archived directories at the time of the restructure; re-measure before applying):

| Shape | Count |
|---|---|
| Scalar `evidence: <value>`, all required fields present | majority |
| List-form `evidence` (`evidence:` + `- item`, or `evidence: [a, b]`) | 3 |
| No `meta.yaml` file at all | 10 |
| `meta.yaml` present but missing `blocked_by` | 3 |
| `meta.yaml` present but missing `evidence` | 1 |

Three facts, checked against git history, shape how this must be done.

### Fact 1: the guard is blind to 10 of the 14 incomplete records

`tests/test_openspec_change_meta.py` globs `openspec/changes/archive/*/meta.yaml` and parses each
hit. A directory with **no** `meta.yaml` produces no hit, so it is not a parse failure — it is
invisible. `KNOWN_LEGACY_ARCHIVE_RECORDS` covers only the 4 directories that have a partial file.
The 10 directories without any `meta.yaml` have no coverage at all.

All 10 have complete task lists (3/3 through 27/27 checked), so they are finished work, not
abandoned drafts.

### Fact 2: the missing values must be reconstructed, not recovered

Git history shows the metadata tooling landed `2026-03-17` (`26858db`, which added
`tools/openspec_change_meta.py`, the template, and the `blocked_by` rule to `AGENTS.md`). But the
4 partial records were *hand-written later*:

| Record | Gap |
|---|---|
| `2026-03-26-exec-import-support` | `blocked_by` |
| `2026-03-26-readme-user-facing-rewrite` | `blocked_by` |
| `2026-05-12-exec-async-warning-status` | `blocked_by` |
| `2026-05-14-relax-runtime-guidance-compile-count-situation` | `evidence` |

So these were never tool-generated — there is no generator output to restore and no diff to revert
to. The correct values have to be **inferred from each change's own content**, which is a judgment
call per record, not a mechanical migration.

A keyword search of the 3 `blocked_by`-gap proposals for dependency language
(`depend|blocked|prerequisite|requires? … change|after … lands`) returns **nothing**. None of them
states a blocking dependency in prose either. That is a real finding, not a search failure — see
Decision 2.

For the 10 missing files, the sibling `meta.yaml` in the same date range plus each change's own
`proposal.md` and completed `tasks.md` are the available evidence.

### Fact 3: list form is the outlier, and its scalar equivalent is already defined

`evidence: tests, manual-check` is exactly the joined form the parser produces for a list input. So
rewriting the three list-form records is not a lossy reinterpretation — it is what the tooling
already reads, written back out. This is "restore the majority form for three outliers", not a
migration of the archive.

## Goals / Non-Goals

**Goals:**

- Every archived directory has a `meta.yaml`, and every one parses, with no name-based exemptions.
- Every archived `evidence` field uses the scalar form.
- Every backfilled value be justifiable from that change's own content, and the justification
  recorded.
- The guard cover the "no `meta.yaml`" case and the "list-form `evidence`" case.

**Non-Goals:**

- Not inferring `blocked_by` dependencies that the change never claimed. Inventing one would put a
  false dependency edge into `openspec_backlog.py`'s dependency graph.
- Not re-deriving `change_type` / `priority` for the 10 from scratch where a defensible reading of
  their proposals gives the same answer; the point is a complete, parseable record.
- Not touching `updated_at` on existing records — see Decision 5.
- Not changing the parser, which keeps accepting list form — see Decision 6.
- Not reordering `evidence` values alphabetically. Written order carries the author's emphasis.
- Not restyling archived records beyond the fields this change adds or rewrites.

## Decisions

### Decision 1: Backfill from each change's own content, and record the reasoning per record

Every inferred value is a claim about a past change. To keep those claims auditable, each backfilled
record gets its justification recorded in a table in this design, not silently written. A future
reader must be able to see that `evidence: tests` was inferred from a `tests.test_*` reference in
that change's tasks, not invented.

### Decision 2: `blocked_by: []` for the 3, and that is a finding not a shrug

None of the 3 records states a dependency in prose and none has a sibling that plausibly blocked it
(the 3 are independent: import support, README rewrite, async warning status). Writing `[]` asserts
"this change had no prerequisites", which is what the content supports. An empty list that means
"unknown" and an empty list that means "none" are different claims; here it means "none, based on
the proposal's silence."

If a human knows of a real dependency, that is a correction to this backfill, not a reason to defer it.

### Decision 3: Rewrite the three list-form records to scalar, preserving order, touching only that line

Only the `evidence` line changes in each of the three records. Comments, key order, quoting style,
and blank lines stay as they are. A normalization pass that also reformats is how an archive stops
being trustworthy as a record.

Doing the rewrite before the backfill means every `meta.yaml` this change writes is already in the
canonical form, so the list-form guard (Decision 4) holds the moment it is added.

### Decision 4: Guard with raw-text and presence assertions, not with a git hook

Extend the real-archive guard with two assertions:

- every directory under `openspec/changes/archive/` **has** a `meta.yaml` — the gap that let 10
  records go unnoticed;
- no archived `meta.yaml` uses list-form `evidence`. This inspects raw text, because parsing
  deliberately accepts both forms and therefore cannot distinguish them.

This keeps both rules enforced in the default suite without adding a commit-time hook, which would
be the first such hook in the repository.

### Decision 5: Leave `updated_at` untouched on existing records

`updated_at` means when the change was last updated. Adding metadata today is not the change being
updated today. Overwriting it would erase real chronology. For the 10 new files, `updated_at` is
taken from the change's own last real commit date, not from today.

### Decision 6: Keep parser support for list form

The temptation after normalizing the archive is to remove list-form acceptance so the form can never
reappear. Rejected: `2026-10-13-fix-change-meta-evidence-list-parsing` exists precisely because a
parser that rejects valid-looking YAML fails on records nobody can see. The archive guard enforces
the canonical form for history; the parser stays tolerant for new hand-written records.

### Decision 7: Delete `KNOWN_LEGACY_ARCHIVE_RECORDS` rather than shrink it

Once all 14 are backfilled the constant has no members. Leaving an empty exemption list in the test
would invite the next person to add a name to it. Removing it is what makes the guard mean "the whole
archive parses."

## Backfill justification table

Filled in during apply (task 2.3), one row per backfilled record:

| Record | Field(s) written | Value(s) | Justification (source in that change) |
|---|---|---|---|

## Risks / Trade-offs

**Inferred values could be wrong** → Decision 1's per-record justification makes them reviewable;
this change is a doc-and-data edit whose entire diff is meant to be read, and the values are
surfaced to the human before archive.

**Rewriting archived history is itself a judgment call** → bounded by Decision 3 and by preserving
every value; the rewrite diff is three `evidence` lines.

**Someone might object to backfilling archives at all** → the alternative is the permanent
name-based exemption, which was explicitly recorded as a scope boundary rather than an end state.

**The guard could reject a legitimately meta-less archive entry** → if a future archived change is
legitimately exempt, that argues for a different archive layout, not for re-adding the exemption list.

**A future author writes list-form `evidence` again** → it parses, and the archive guard fails it
once archived. `AGENTS.md` (via `define-evidence-as-multi-valued`) states scalar as canonical.
