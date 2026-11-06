# Tasks

## 1. Establish the baseline the cases must not disturb

- [x] 1.1 Record the current real-host suite shape: case count in
      `tests/test_real_host_integration.py`, which classes share the host device, and the Editor
      launch count for a full run. Verify by `grep -c "    def test_" tests/test_real_host_integration.py`
      and by reading the shared-device class, and write both numbers into the change directory so
      task 3.3 has something to compare against.
- [x] 1.2 Confirm the default staleness behavior the reset case must be distinguished from: read
      how `--stale-module-policy` and the same-invocation server-owned reset are implemented, and
      write down which observable would still change if `--reset-jsenv-before-exec` were a no-op.
      The case is only worth writing if that observable exists; if it does not, stop and report
      that the flag is unobservable end to end instead of writing a case that cannot fail.

  Evidence: `baseline-and-discriminator.md`. 52 cases across 5 shared-device classes, 5
  interactive launches + 1 cached batch preflight per full run. The discriminator is
  `ctx.globals` continuity plus `recovery.reason == "explicit_request"`; both exist.

## 2. Write the cases

- [x] 2.1 Add the import-resolution case to the existing shared-device class in
      `tests/test_real_host_integration.py`: write a module fixture, run `exec --code` with a
      relative `import` and `--import-base-url` pointing at the fixture directory, and assert the
      imported exported value appears in `result`. Verify the case fails when the fixture module
      is absent, so it is asserting resolution and not merely absence of an error.
- [x] 2.2 Add the explicit-reset case: store a marker in `ctx.globals` in one exec, then run a
      second exec with `--reset-jsenv-before-exec` and an **unchanged** module, asserting the
      marker is gone. Verify the case fails against a scratch build where the flag is ignored, and
      passes against the real one — this is the discrimination established in 1.2.
- [x] 2.3 Make both cases clean up their fixtures through the suite's existing per-case reset
      rather than their own teardown path. Verify by running them and then
      `git -C <host repo> status --short` on the host project, which must report no new or
      modified tracked file.
- [x] 2.4 If the new cases introduce device state the mocked reset tests must know about, extend
      `tests/test_real_host_reset.py` accordingly. Verify
      `python -m unittest tests.test_real_host_reset` passes; if no device state was added, record
      that in the change directory instead of inventing a case.

## 3. Run them where the surface is version-sensitive

- [x] 3.1 Run the two new cases against the 2.2.2 host and verify both pass, capturing the
      responses as evidence in the change directory.

  Both `ok` in 137 s once `_restore_active_scene` was repaired (it could not run at all
  before — see `blocked-2-2-2-host.md`). Evidence: `validation-evidence.md`.
- [x] 3.2 Run the same two cases against a 3.0.0 host — clearing its embedded package shadow
      first and restoring it afterwards — and verify both pass, and that the host's
      `git status --short` is empty once restored.
- [x] 3.3 Verify the suite's Editor launch count is unchanged from the 1.1 baseline with the new
      cases present, so the cost-scales-with-cases requirement still holds. Record both numbers.
- [x] 3.4 Run the mocked default suite as documented and verify `OK` with no new failures.

  Evidence for 3.2–3.4: `validation-evidence.md`. Both cases `ok` on tree5 in 133 s;
  1 interactive launch + 1 batch preflight for the class, unchanged from baseline; default
  suite `Ran 877 tests ... OK`.

## 4. Retire the scratch probe and close out

- [x] 4.1 Retire `.tmp/puerts2_e2e_probe.py` as the source of this evidence and record in the
      change directory which real-host cases replaced each of its five steps, so the
      `support-puerts-2x-jsenv` evidence trail still resolves after `.tmp/` is cleaned.

  The step-by-step mapping is recorded in `apply-notes-2-4-and-4-1.md`. The **file itself is
  deliberately not deleted yet**: because task 3.1 is blocked, the probe is still the only
  artifact that has ever demonstrated import/reset behavior end to end on a 2.2.2 host.
  Deleting it now would destroy evidence with no replacement. Delete it once task 3.1 can pass.
- [x] 4.2 Run `openspec validate cover-import-and-reset-jsenv-real-host --strict` and verify it
      passes.
- [x] 4.3 Write the closeout finding summary stating either `No new follow-up work identified`
      or `New follow-up candidates identified`.

## Workflow follow-up

- Archive with `openspec archive cover-import-and-reset-jsenv-real-host` once review
  requirements are satisfied, then verify
  `openspec/specs/validation-host-integration/spec.md` carries the new coverage requirement.
- The HTTP form of `--import-base-url` is a separate `exec-import-support` requirement and is
  deliberately not covered here; raise it at closeout as its own candidate rather than widening
  this change, since it needs a local HTTP fixture the suite does not currently have.

## Closeout finding summary (task 4.3)

**New follow-up candidates identified.** All 13 tasks are complete and verified on both
hosts.

1. **`product-improvement` — a filesystem `--import-base-url` defeats `ctx.globals`
   continuity.** `BuildEntrySpecifier` names the entry module after the request id, so each
   exec with a filesystem base URL writes a new entry file and sweeps the old one;
   `CheckModuleStaleness` then reports it as changed, and the default `auto-reset` policy
   resets the JsEnv on every exec. JsEnv-scoped state therefore cannot survive across execs
   whenever a filesystem `--import-base-url` is used — which is exactly the continuity the CLI
   help says `--stale-module-policy error` exists to protect. Found while writing task 2.2;
   recorded in `validation-evidence.md`.
2. **`validation-gap` — the HTTP form of `--import-base-url` remains uncovered.** As the
   workflow follow-up already anticipated: it needs a local HTTP fixture the suite does not
   have. Unchanged by this change, and deliberately not absorbed.
3. **`workflow-improvement` — the shared reset helper's PuerTS-version fragility is worth a
   guard.** `_restore_active_scene` depends on internal Unity reflection that 2.2.2 could not
   bind; it failed silently for every case on that host and went unnoticed because the helper
   landed before the 2.2.2 host was ever run through this suite. A dedicated case that pins
   the reset helper itself (`_restore_active_scene` returns `cleared: true` with a clean
   `git status`) would fail loudly on the next PuerTS major instead of poisoning all 54
   shared-device cases equally.
