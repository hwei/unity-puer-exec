# Tasks

## 1. Establish the baseline the cases must not disturb

- [ ] 1.1 Record the current real-host suite shape: case count in
      `tests/test_real_host_integration.py`, which classes share the host device, and the Editor
      launch count for a full run. Verify by `grep -c "    def test_" tests/test_real_host_integration.py`
      and by reading the shared-device class, and write both numbers into the change directory so
      task 3.3 has something to compare against.
- [ ] 1.2 Confirm the default staleness behavior the reset case must be distinguished from: read
      how `--stale-module-policy` and the same-invocation server-owned reset are implemented, and
      write down which observable would still change if `--reset-jsenv-before-exec` were a no-op.
      The case is only worth writing if that observable exists; if it does not, stop and report
      that the flag is unobservable end to end instead of writing a case that cannot fail.

## 2. Write the cases

- [ ] 2.1 Add the import-resolution case to the existing shared-device class in
      `tests/test_real_host_integration.py`: write a module fixture, run `exec --code` with a
      relative `import` and `--import-base-url` pointing at the fixture directory, and assert the
      imported exported value appears in `result`. Verify the case fails when the fixture module
      is absent, so it is asserting resolution and not merely absence of an error.
- [ ] 2.2 Add the explicit-reset case: store a marker in `ctx.globals` in one exec, then run a
      second exec with `--reset-jsenv-before-exec` and an **unchanged** module, asserting the
      marker is gone. Verify the case fails against a scratch build where the flag is ignored, and
      passes against the real one — this is the discrimination established in 1.2.
- [ ] 2.3 Make both cases clean up their fixtures through the suite's existing per-case reset
      rather than their own teardown path. Verify by running them and then
      `git -C <host repo> status --short` on the host project, which must report no new or
      modified tracked file.
- [ ] 2.4 If the new cases introduce device state the mocked reset tests must know about, extend
      `tests/test_real_host_reset.py` accordingly. Verify
      `python -m unittest tests.test_real_host_reset` passes; if no device state was added, record
      that in the change directory instead of inventing a case.

## 3. Run them where the surface is version-sensitive

- [ ] 3.1 Run the two new cases against the 2.2.2 host and verify both pass, capturing the
      responses as evidence in the change directory.
- [ ] 3.2 Run the same two cases against a 3.0.0 host — clearing its embedded package shadow
      first and restoring it afterwards — and verify both pass, and that the host's
      `git status --short` is empty once restored.
- [ ] 3.3 Verify the suite's Editor launch count is unchanged from the 1.1 baseline with the new
      cases present, so the cost-scales-with-cases requirement still holds. Record both numbers.
- [ ] 3.4 Run the mocked default suite as documented and verify `OK` with no new failures.

## 4. Retire the scratch probe and close out

- [ ] 4.1 Retire `.tmp/puerts2_e2e_probe.py` as the source of this evidence and record in the
      change directory which real-host cases replaced each of its five steps, so the
      `support-puerts-2x-jsenv` evidence trail still resolves after `.tmp/` is cleaned.
- [ ] 4.2 Run `openspec validate cover-import-and-reset-jsenv-real-host --strict` and verify it
      passes.
- [ ] 4.3 Write the closeout finding summary stating either `No new follow-up work identified`
      or `New follow-up candidates identified`.

## Workflow follow-up

- Archive with `openspec archive cover-import-and-reset-jsenv-real-host` once review
  requirements are satisfied, then verify
  `openspec/specs/validation-host-integration/spec.md` carries the new coverage requirement.
- The HTTP form of `--import-base-url` is a separate `exec-import-support` requirement and is
  deliberately not covered here; raise it at closeout as its own candidate rather than widening
  this change, since it needs a local HTTP fixture the suite does not currently have.
