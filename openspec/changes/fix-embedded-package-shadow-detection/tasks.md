## 1. Identity-based detection

- [x] 1.1 Rewrite `detect_embedded_package_shadowing` to scan the immediate children of the manifest's parent directory and flag every directory whose `package.json` declares the formal package name.
- [x] 1.2 Skip directories with no `package.json`, an unparseable one, or a different declared name, without failing the preparation run.
- [x] 1.3 Preserve the existing exemption for a candidate that resolves to the repository-local package root, applied per candidate so a symlink or junction under another name is still exempt.

## 2. Report shape

- [x] 2.1 Report every shadowing directory, keeping the existing single `embedded_package_path` field populated for the common single-copy case so current consumers are unaffected.
- [x] 2.2 Confirm the emitted JSON stays machine-readable and that a consumer reading only the existing fields sees no change in the single-copy case.

## 3. Tests

- [x] 3.1 Add a test for a shadowing directory renamed away from the package name, asserting it is still reported — the case that produced the false negative.
- [x] 3.2 Add tests for the clean host, the intended-package-root exemption, and multiple shadowing directories.
- [x] 3.3 Add tests for an unrelated package directory, a directory with no `package.json`, and one with malformed JSON, asserting none are flagged and none abort the run.
- [x] 3.4 Confirm the previously passing single-directory cases still behave the same.

## 4. Documentation

- [x] 4.1 Record in `validation-host-integration/how-to-run.md` that Unity identifies embedded packages by the `name` in `package.json`, so renaming the directory does not clear the shadow.
- [x] 4.2 State the working remedy: move or remove the directory out of `Packages/`.

## 5. Validation and closeout

- [x] 5.1 Run the repository unit suite and confirm no regressions.
- [x] 5.2 Run the tool against the real validation host and confirm it reports the host's true state.
- [x] 5.3 Reproduce the originating false negative end to end: place a copy of the package under a non-matching directory name in a temporary host layout and confirm the tool now reports it.
- [x] 5.4 Run `openspec validate fix-embedded-package-shadow-detection` and confirm the change remains valid.
- [x] 5.5 Record the apply closeout finding summary, stating either `No new follow-up work identified` or `New follow-up candidates identified`.
