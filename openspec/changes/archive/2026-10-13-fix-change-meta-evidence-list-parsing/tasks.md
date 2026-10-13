## 1. Fix the parser

- [x] 1.1 Handle `evidence` the way `blocked_by` is handled, so scalar, inline-list, and block-list forms are all accepted. Verify: all three forms parse, each asserted.
- [x] 1.2 Define how a multi-value `evidence` collapses into the single-value `ChangeMeta.evidence`, and pin it with a test. Verify: the join format is deterministic and does not silently discard a value.
- [x] 1.3 Improve the diagnostic so it shows the parsed values and the accepted set instead of `Unsupported evidence '[tests]'`. Verify: the message no longer implies the value itself is forbidden.

## 2. Coverage

- [x] 2.1 Add coverage asserting each accepted `evidence` form parses to the expected value. Verify: scalar, inline-list, and block-list are each named.
- [x] 2.2 Add a guard that walks `openspec/changes/archive/*/meta.yaml` and reports unparseable records. Verify: the guard runs against the real archive, not synthetic fixtures.
- [x] 2.3 Decide and state explicitly whether the guard fails on the known legacy records that are missing required fields, or excludes them by a stated reason. Verify: the decision is recorded, not left implicit.

  **Decision (recorded):** the guard *fails* on any record that fails for a reason other than
  missing required fields, and *excludes by name* only the four records that predate the
  `blocked_by`/`evidence` required-field rule. Recorded as
  `KNOWN_LEGACY_ARCHIVE_RECORDS` in `tests/test_openspec_change_meta.py`. The guard also
  asserts that each tolerated record fails *only* with
  `Missing required metadata fields`, so an `evidence` failure can never be waved through as
  legacy. Rationale: those four records fail for a governance-history reason outside this
  change's scope, whereas `evidence` list parsing is exactly what this change fixes.

- [x] 2.4 Confirm `dump_meta` still round-trips after the change. Verify: a parse of dumped output re-parses unchanged.

## 3. Closeout

- [x] 3.1 Run the default suite and confirm no regression.
- [x] 3.2 Run `openspec validate fix-change-meta-evidence-list-parsing --strict` and `openspec validate --all`.
- [x] 3.3 Raise the separate decision on whether to rewrite the three archived records that carry the list form, without performing it in this change.

  **Raised, not performed.** Open question for a follow-up change: should
  `2026-04-01-remove-wait-until-ready-command`,
  `2026-10-13-make-base-url-exec-refresh-recoverable`, and
  `2026-10-13-reproduce-play-mode-transport-reset-flake` be rewritten to a scalar `evidence`?

  - **For rewriting:** archived records are inputs to tooling, not an append-only log; one
    canonical form removes a class of parser special-case forever.
  - **Against rewriting:** archived history is immutable record; rewriting it to accommodate a
    parser is a governance decision that should be taken on its own, not as a side effect.
  - **Current state:** the parser accepts all three as-is, so the rewrite is cosmetic, not a
    blocker. Leaving them is safe; the list form stays covered by tests against the real archive.

- [x] 3.4 Complete the apply closeout review, including whether `AGENTS.md` should formally define `evidence` as multi-valued.

  **Closeout finding: New follow-up candidates identified.**

  | Candidate | Category | Context |
  |---|---|---|
  | Rewrite the three archived records carrying the `evidence` list form | `workflow-improvement` | Argument for and against recorded under 3.3; parser accepts them today, so this is a governance choice, not a blocker. |
  | Define `evidence` as formally multi-valued in `AGENTS.md` | `workflow-improvement` | `AGENTS.md` currently lists allowed `evidence` values without saying whether one record may name several. The parser now accepts several and joins them with `", "`, and `tools/openspec_backlog.py:evidence_rank` ranks a joined value by its strongest entry. Formalizing this documents behavior the code already has. |
  | Decide whether the four legacy records missing `blocked_by`/`evidence` get backfilled | `validation-gap` | They are currently tolerated only by name in `tests/test_openspec_change_meta.py:KNOWN_LEGACY_ARCHIVE_RECORDS`. If backfilled, that constant can shrink. |
  | `tools/openspec_backlog.py --evidence` filter does exact match on a possibly joined string | `tooling-improvement` | `--evidence tests` will not match a record whose `evidence` is `"tests, cli-transcript"`. Now reachable because multi-value input parses. |

  All four require human discussion before any follow-up change is created.

  **Note on this change's own record:** `meta.yaml` keeps the scalar `evidence: tests`, so no
  self-application of the list form is needed here.