# Tasks

## 1. Declare the root

- [x] 1.1 Add `Assets/__codex_host_reset` to `DECLARED_VALIDATION_TEMP_ROOTS` in
      `tools/cleanup_validation_host.py`, alongside the existing declared roots and following the same
      `Path("Assets") / ...` form. Verify: `python -m unittest tests.test_cleanup_validation_host_tool`
      passes and the tool's inventory report names the new root.
- [x] 1.2 Confirm the refusal path is untouched: a requested path outside the inventory still refuses
      and names the inventory, so declaring a root changed only what the harness itself cleans.
      Verify: the existing refusal cases in `tests.test_cleanup_validation_host_tool` still pass
      unmodified.

## 2. Inventory-versus-suite guard

- [x] 2.1 Add a guard to `tests/test_cleanup_validation_host_tool.py` that reads the
      repository-owned asset roots the real-host suite creates — including
      `HOST_RESET_SCENE_RELATIVE` and the probe directory the suite writes compile-triggering and
      never-imported probes into — and fails naming any root the declared inventory does not cover.
      Derive the roots by importing the suite's own path constants (for example
      `tests.test_real_host_integration.HOST_RESET_SCENE_RELATIVE`) or by scanning that module for
      `Assets/...` path literals, not from a second hand-maintained list, so the guard cannot drift
      the same way the inventory did. Importing the module must not require a Unity Editor.
      Verify: `python -m unittest tests.test_cleanup_validation_host_tool` passes.
- [x] 2.2 Prove the guard has teeth: temporarily point it at an undeclared root and confirm it fails
      with the root named, then restore it. Verify: the deliberate failure and its message are
      recorded in the closeout summary.
- [x] 2.3 Run the default mocked suite as documented in
      `openspec/specs/validation-host-integration/how-to-run.md`. Verify: every listed module passes
      with no new failure or skip, and the guard runs without a Unity Editor or a validation host.

## 3. Real-host residue check

- [ ] 3.1 Run a real-host class against the host in `.env` and confirm that after its teardown the
      host project's version-control status reports no repository-owned residue, including no
      `__codex_host_reset` directory or metadata. Verify:
      `UNITY_PUER_EXEC_RUN_REAL_HOST_TESTS=1 python -m unittest tests.test_real_host_integration.RefreshOnChangeRealHostTests`
      passes and the host status afterwards is empty, with the transcript captured in the closeout
      summary.
- [ ] 3.2 Clean the residue a previous run already left, if any, so the host starts from the state
      this change assumes. Verify: the host project's version-control status is empty before the 3.1
      run and the removal is recorded in the closeout summary.

## Workflow follow-up

- Archive the change with `openspec archive declare-host-reset-scene-for-cleanup` once the real-host
  residue check is recorded and the review requirements are satisfied.
- Verify the archived result: `openspec validate --all` and
  `python -m unittest tests.test_openspec_spec_hygiene`.
