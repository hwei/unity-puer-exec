## 1. Current Model Analysis

- [x] 1.1 Inventory which current `meta.yaml` status values are still necessary as explicit manual repository decisions versus which ones are candidates for derivation.
- [x] 1.2 Reproduce how `tools/openspec_backlog.py`, archived change state, and repository governance rules currently interact when recommending or excluding work.

## 2. Derived Recommendation Exploration

- [x] 2.1 Compare at least two candidate models: a minimal-manual model that retains only explicit superseded disposition and a hybrid model that still preserves one or more manual active/blocked hints.
- [x] 2.2 Evaluate Git commit distance against timestamp-based recency as a recommendation signal and record the preferred interpretation.
- [x] 2.3 Decide how missing `blocked_by` references should affect recommendation eligibility versus diagnostic output.

## 3. Follow-up Path

- [x] 3.1 Update the change artifacts with the recommended backlog model and the durable-spec changes it would require.
- [x] 3.2 Decide whether to archive this spike directly or convert it into a follow-up implementation-oriented change.
