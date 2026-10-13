## Context

14 archived directories are missing required `meta.yaml` content. Two facts, measured and then
checked against git history, change how this must be done.

### Fact 1: the guard is blind to 10 of the 14

`tests/test_openspec_change_meta.py` globs `openspec/changes/archive/*/meta.yaml` and parses each
hit. A directory with **no** `meta.yaml` produces no hit, so it is not a parse failure — it is
invisible. `KNOWN_LEGACY_ARCHIVE_RECORDS` covers only the 4 directories that have a partial file.
The 10 directories without any `meta.yaml` have no coverage at all.

All 10 have complete task lists (3/3 through 27/27 checked), so they are finished work, not
abandoned drafts.

### Fact 2: the values must be reconstructed, not recovered

Git history shows the metadata tooling landed `2026-03-17` (`26858db`, which added
`tools/openspec_change_meta.py`, the template, and the `blocked_by` rule to `AGENTS.md`). But the
4 partial records were *hand-written later*:

| Record | `meta.yaml` added | Gap |
|---|---|---|
| `2026-03-26-exec-import-support` | 2026-03-27 (`71c2a23`) | `blocked_by` |
| `2026-05-12-exec-async-warning-status` | 2026-05-12 (`b96a945`) | `blocked_by` |
| `2026-05-14-relax-runtime-guidance-compile-count-situation` | 2026-05-14 (`712a57d`) | `evidence` |

So these were never tool-generated — there is no generator output to restore and no diff to revert
to. The correct values have to be **inferred from each change's own content**, which is a judgment
call per record, not a mechanical migration.

A keyword search of the 3 `blocked_by`-gap proposals for dependency language
(`depend|blocked|prerequisite|requires? … change|after … lands`) returns **nothing**. None of them
states a blocking dependency in prose either. That is a real finding, not a search failure — see
Decision 2.

For the 10 missing files, the sibling `meta.yaml` in the same date range plus each change's own
`proposal.md` and completed `tasks.md` are the available evidence.

## Goals / Non-Goals

**Goals:**

- Every archived directory parses, with no name-based exemptions.
- Every written value be justifiable from that change's own content, and the justification recorded.
- The guard cover the "no `meta.yaml`" case, which it currently does not.

**Non-Goals:**

- Not inferring `blocked_by` dependencies that the change never claimed. Inventing one would put a
  false dependency edge into `openspec_backlog.py`'s dependency graph.
- Not re-deriving `change_type` / `priority` for the 10 from scratch where a defensible reading of
  their proposals gives the same answer; the point is a complete, parseable record.
- Not touching `updated_at` — it records when the change was last updated, and backfilling fields
  today does not retroactively change that. This is Decision 4.

## Decisions

### Decision 1: Backfill from each change's own content, and record the reasoning per record

Every inferred value is a claim about a past change. To keep those claims auditable, each backfilled
record gets its justification recorded in this change's artifacts (a table here, or an
`evidence`-adjacent comment), not silently written. A future reader must be able to see that
`evidence: tests` was inferred from a `tests.test_*` reference in that change's tasks, not invented.

### Decision 2: `blocked_by: []` for the 3, and that is a finding not a shrug

None of the 3 records states a dependency in prose and none has a sibling that plausibly blocked it
(the 3 are independent: import support, README rewrite, async warning status). Writing `[]` asserts
"this change had no prerequisites", which is what the content supports. Recording this explicitly
matters: an empty list that means "unknown" and an empty list that means "none" are different claims,
and here it means "none, based on the proposal's silence."

If a human knows of a real dependency, that is a correction to this backfill, not a reason to defer it.

### Decision 3: Add a guard assertion for missing `meta.yaml`, not just unparseable ones

Extend the guard to assert every directory under `openspec/changes/archive/` **has** a `meta.yaml`.
This is the gap that let 10 records go unnoticed. Cheap to check, and it is the assertion that would
have caught them.

### Decision 4: Leave `updated_at` untouched

`updated_at` means when the change was last updated. Adding metadata today is not the change being
updated today. Overwriting it would erase real chronology and make the archive lie about its own
history — a worse defect than the one being fixed. For the 10 new files, `updated_at` is taken from
the change's own last real commit date, not from today.

### Decision 5: Delete `KNOWN_LEGACY_ARCHIVE_RECORDS` rather than shrink it

Once all 14 are backfilled the constant has no members. Leaving an empty exemption list in the test
would invite the next person to add a name to it. Removing it is what makes the guard mean "the whole
archive parses."

## Risks / Trade-offs

**Inferred values could be wrong** → Decision 1's per-record justification makes them reviewable;
this change is a doc-and-data edit whose entire diff is meant to be read.

**Someone might object to backfilling archives at all** → the alternative is the permanent
name-based exemption from `2026-10-13-fix-change-meta-evidence-list-parsing`, which was explicitly
recorded as a scope boundary rather than an end state.

**The guard could reject a legitimately meta-less archive entry** → if a future archived change is
legitimately exempt, that argues for a different archive layout, not for re-adding the exemption list.