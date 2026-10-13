## 1. Fix the parser

- [ ] 1.1 Handle `evidence` the way `blocked_by` is handled, so scalar, inline-list, and block-list forms are all accepted. Verify: all three forms parse, each asserted.
- [ ] 1.2 Define how a multi-value `evidence` collapses into the single-value `ChangeMeta.evidence`, and pin it with a test. Verify: the join format is deterministic and does not silently discard a value.
- [ ] 1.3 Improve the diagnostic so it shows the parsed values and the accepted set instead of `Unsupported evidence '[tests]'`. Verify: the message no longer implies the value itself is forbidden.

## 2. Coverage

- [ ] 2.1 Add coverage asserting each accepted `evidence` form parses to the expected value. Verify: scalar, inline-list, and block-list are each named.
- [ ] 2.2 Add a guard that walks `openspec/changes/archive/*/meta.yaml` and reports unparseable records. Verify: the guard runs against the real archive, not synthetic fixtures.
- [ ] 2.3 Decide and state explicitly whether the guard fails on the known legacy records that are missing required fields, or excludes them by a stated reason. Verify: the decision is recorded, not left implicit.
- [ ] 2.4 Confirm `dump_meta` still round-trips after the change. Verify: a parse of dumped output re-parses unchanged.

## 3. Closeout

- [ ] 3.1 Run the default suite and confirm no regression.
- [ ] 3.2 Run `openspec validate fix-change-meta-evidence-list-parsing --strict` and `openspec validate --all`.
- [ ] 3.3 Raise the separate decision on whether to rewrite the three archived records that carry the list form, without performing it in this change.
- [ ] 3.4 Complete the apply closeout review, including whether `AGENTS.md` should formally define `evidence` as multi-valued.