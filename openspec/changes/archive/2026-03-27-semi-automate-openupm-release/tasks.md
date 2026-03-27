## 1. Release Helper Implementation

- [x] 1.1 Add `tools/release_openupm.py` with argument parsing for `--version`, `--commit`, `--tag`, `--dry-run`, and the opt-in real-host validation flag.
- [x] 1.2 Implement release preflight checks for clean working tree, existing local/remote `v<version>` tag detection, and release-state refusal paths before any version edit occurs.
- [x] 1.3 Implement the real execution flow: update `packages/com.txcombo.unity-puer-exec/package.json`, run the default mocked/unit release test suite, optionally run real-host validation, optionally create a release commit, optionally create a local source tag, and print explicit next-step guidance without pushing.
- [x] 1.4 Implement pure `--dry-run` behavior that reports the planned version change, validations, tests, and optional git actions without changing repository state.

## 2. Validation Coverage

- [x] 2.1 Add or update unit tests for argument combinations, version rewrite behavior, dirty-tree and duplicate-tag refusal paths, and `--tag` requiring committed release state.
- [x] 2.2 Add or update tests that prove `--dry-run` performs no state changes and that the helper reports the default versus opt-in real-host test plans correctly.

## 3. Workflow Closeout

- [x] 3.1 Add maintainer-facing workflow guidance for the new helper, including example commands and the explicit boundary that remote push still triggers the existing CI release pipeline.
- [x] 3.2 Validate the helper manually in a safe local release-preparation scenario and capture the result needed to close the change cleanly.
