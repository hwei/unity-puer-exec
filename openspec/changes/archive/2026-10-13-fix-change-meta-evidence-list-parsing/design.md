## Context

`parse_meta_text` is a small hand-rolled line parser. It supports three shapes: a scalar
(`key: value`), an inline empty list (`key: []`), and a block list (`key:` followed by `- item`
lines). `normalize_meta` then validates each field — and does so inconsistently:

```python
blocked_values: list[str] = []
if blocked_by in ("[]", None): ...
elif isinstance(blocked_by, list): blocked_values = [str(item) for item in blocked_by]
else: raise ValueError("blocked_by must be a list.")
...
evidence=_validate_choice(str(raw["evidence"]), ALLOWED_EVIDENCE, "evidence"),
```

`blocked_by` branches on type; `evidence` stringifies whatever it got. So the block-list form
the parser can produce is itself rejected by the validator downstream.

`dump_meta` always writes a scalar and round-trips cleanly, so the defect only affects
hand-written or tool-authored multi-value input. Nothing in the default suite reads the real
archive, so existing tests stay green while the real records are unparseable.

## Goals / Non-Goals

**Goals:**

- Make `evidence` accept scalar, inline-list, and block-list forms consistently with
  `blocked_by`.
- Make the failure diagnostic actionable.

**Non-Goals:**

- Not backfilling the four older records that fail for a different reason (missing required
  fields predating `AGENTS.md`).
- Not adding a general-purpose YAML dependency.
- Not deciding whether `evidence` should formally become multi-valued in `AGENTS.md`.

## Decisions

### Decision 1: Keep `evidence` typed as a string in `ChangeMeta`, fix only the input handling

The reported bug is that valid input is rejected. Widening `ChangeMeta.evidence` to a tuple
would ripple into `dump_meta`, the backlog record model, and every consumer that formats it,
for no behavioral gain — the backlog tool only needs a display value. Normalizing the parsed
input and keeping the single-value representation is the smaller correct fix.

The design must therefore specify how a multi-value input collapses: a deterministic join
(the format the existing inline-list records already use) rather than silently keeping only the
first entry, which would discard evidence without telling anyone.

### Decision 2: Report the offending value, not its stringification

`Unsupported evidence '[tests]'` is actively misleading — it implies `[tests]` is a rejected
literal. The message should show the parsed values and the accepted set, so the reader can see
immediately that the value was mis-parsed rather than forbidden.

### Decision 3: Do not silently normalize the archived records as part of this change

Three archived changes carry the unsupported list form. Rewriting archived records is a
governance decision about immutable history, not a side effect of a parser fix. This change
should make the parser accept them; whether to also rewrite them should be raised separately,
with the argument for each stated.

Note that one of the three is
`2026-10-13-reproduce-play-mode-transport-reset-flake`, created earlier today by this same
session — an in-repo precedent now exists for writing a list and having it fail, so the
"nobody writes that form" defense no longer holds.

### Decision 4: Add coverage that reads the real archive

The reason this survived is that tests only ever used synthetic fixtures with single-valued
`evidence`. A guard that walks `openspec/changes/archive/*/meta.yaml` and parses each file
would have caught it. Such a guard must tolerate the known-unparseable legacy records without
failing, or it would block on a problem outside this change's scope — the task list requires
deciding that explicitly rather than discovering it mid-implementation.

## Risks / Trade-offs

**A join format becomes a de facto format** → risk that hand-written records drift toward
whatever the join happens to produce. The format must be pinned by a test and documented in
`AGENTS.md` only if multi-value is formally adopted.