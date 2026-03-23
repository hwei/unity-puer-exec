## 1. Metadata And Contract

- [x] 1.1 Decide and document the narrowed meaning of `meta.yaml.status` for repository backlog semantics while preserving file-format compatibility.
- [x] 1.2 Update change-local specs so backlog recommendation, superseded handling, and governance guidance match the derived model.

## 2. Backlog Tooling

- [x] 2.1 Refactor `tools/openspec_backlog.py` to compute derived eligibility from archive state, superseded disposition, resolved prerequisites, and missing-dependency diagnostics.
- [x] 2.2 Add Git commit distance as a deterministic ranking signal and expose the reasoning in human-readable and JSON output.
- [x] 2.3 Decide and implement how compatibility filters such as `--status` should behave under the new model.

## 3. Validation

- [x] 3.1 Extend repository tests to cover derived eligibility, missing dependency diagnostics, superseded exclusion, and Git-distance ranking behavior.
- [x] 3.2 Validate the updated backlog outputs against representative local repository states and capture any remaining workflow caveats in the change artifacts.
