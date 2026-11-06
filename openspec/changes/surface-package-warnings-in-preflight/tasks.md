# Tasks

## 1. Parse warnings and attribute them

- [ ] 1.1 Extend the diagnostic pattern in `tools/preflight_compile_check.py` to capture severity
      alongside the code, keeping `_LOCATION_RE` and the returned dict shape shared with the
      existing error path. Verify `parse_compile_errors` still returns byte-identical results for
      the log fixtures in `tests/test_preflight_compile_check.py`:
      `python -m unittest tests.test_preflight_compile_check`.
- [ ] 1.2 Add an attribution helper that decides package ownership from a diagnostic's `file`,
      normalizing separators and requiring the package-name component under a `packages` or
      `Packages` directory. Verify with unit cases covering all four shapes: the absolute
      repository path a `file:` wiring produces, a host-relative embedded-copy path, a
      third-party package path such as `com.unity.render-pipelines.core`, and a diagnostic with
      `file` of `None`.
- [ ] 1.3 Add `parse_package_warnings(log_text)` returning the same dict shape for
      package-attributable warnings only. Verify it returns exactly three entries for the real
      `CS0618` log lines recorded in
      `openspec/changes/archive/2026-11-06-support-puerts-2x-jsenv/validation-evidence.md`, and
      zero for a log whose only warnings come from other packages.

## 2. Decide and report

- [ ] 2.1 Add the additive `package_warnings` key to every non-skipped result payload, leaving
      `diagnostics` meaning `error CS` only. Verify the existing payload assertions in
      `tests/test_preflight_compile_check.py` still pass unmodified, which is the evidence the
      change is additive rather than a reshape.
- [ ] 2.2 Fail the run when `package_warnings` contains a deprecation code (`CS0618`, `CS0619`),
      with a `kind` value distinct from the compile-failure kind and a `reason` naming the count.
      Verify a unit case asserting the failure payload carries the code, the file, and the line,
      and that a caller can distinguish it from a compile error without parsing messages.
- [ ] 2.3 Report but do not fail on any other package-attributable warning. Verify a unit case
      where a non-deprecation package warning leaves `status: passed` while
      `package_warnings` is non-empty.
- [ ] 2.4 Add `--strict-package-warnings`, which fails on any package-attributable warning.
      Verify both directions in unit cases: the same log passes by default and fails under the
      flag.
- [ ] 2.5 Extend `format_failure_detail` so a deprecation failure renders the same human-usable
      multi-line detail as a compile failure. Verify the rendered text names the file, position,
      code, and message.

## 3. Prove the gate on real hosts

- [ ] 3.1 Run `python tools/preflight_compile_check.py` against the 2.2.2 host and verify
      `status: passed` with an empty `package_warnings` — the current tree is clean, so turning
      the gate on must not change the answer.
- [ ] 3.2 Wire and run the same preflight against a 3.0.0 host (clearing its embedded shadow
      first, then restoring it) and verify `status: passed` with an empty `package_warnings`.
      Record both runs in the change directory.
- [ ] 3.3 Replay the motivating defect: in a scratch copy of the package, restore the one-sided
      `"expression": "[3.0.0"` from `support-puerts-2x-jsenv`, run the preflight against the 3.0.0
      host, and verify it now **fails** naming `CS0618` and the three source lines. This is the
      task that proves the change does what it was created for; record the failure payload.
- [ ] 3.4 Confirm the real-host suite inherits the behavior without a separate code path: verify
      it calls the same preflight entry point, and that a deprecation failure surfaces as a run
      failure before an interactive Editor is launched.

## 4. Documentation and closeout readiness

- [ ] 4.1 Update the preflight output description in
      `openspec/specs/validation-host-integration/how-to-run.md` to name `package_warnings`, the
      deprecation failure, and the escalation flag. Verify the documented key list matches the
      keys the tool actually emits, by comparing the doc against a real payload.
- [ ] 4.2 Run the mocked default suite as documented and verify `OK` with no new failures.
- [ ] 4.3 Run `openspec validate surface-package-warnings-in-preflight --strict` and verify it
      passes.
- [ ] 4.4 Write the closeout finding summary stating either `No new follow-up work identified`
      or `New follow-up candidates identified`, and record the evidence from group 3 in the
      change directory.

## Workflow follow-up

- Archive with `openspec archive surface-package-warnings-in-preflight` once review requirements
  are satisfied, then verify `openspec/specs/validation-host-integration/spec.md` carries the
  amended preflight requirement and the new attribution requirement.
- Consider whether the same attribution rule belongs in `tools/run_editmode_tests.py`, which
  reads a batch log of its own. Do not absorb it into this change; raise it at closeout.
