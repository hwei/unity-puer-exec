# Tasks

## 1. Record harness ownership at the write site

- [ ] 1.1 Add a harness-owned path set to `UnityPuerExecServer.cs` beside
      `PendingTempEntryPaths`, normalized the same way `LocalModuleFingerprints` normalizes
      (`NormalizeLocalModulePath`, `/`-separated), and document in place why it is separate
      from the pending-deletion set (design D2: that set is mutated on cleanup, which is
      exactly when membership must still be recognizable).
- [ ] 1.2 Register a path in that set immediately after the successful write of the
      per-request entry module in `StartJobEvaluation`, before `execLoader.SetContext` and
      therefore before the loader can read it. Verify by inspection that the add precedes the
      earliest possible read, since a read recorded first cannot be un-recorded.
- [ ] 1.3 Remove the path again on both cleanup paths — `CleanupTempEntryFile` and
      `SweepPendingTempEntryFiles` — next to the existing `PendingTempEntryPaths` mutation.
      Verify by inspection that every add has a paired remove on both the normal and the
      exception path.

## 2. Guard the ledger

- [ ] 2.1 Add an ownership predicate and guard `RecordLocalModuleRead` so a harness-owned path
      returns before a fingerprint is stored. Do not filter inside `CheckModuleStaleness`:
      keeping the ledger caller-only is the point (design D3).
- [ ] 2.2 Keep a narrow name-based fallback for a harness entry whose membership was lost —
      for example after a server restart mid-request — but require the parent directory to be
      a base directory this process wrote into. Verify a caller file named
      `__puer_exec_entry_x.js` outside any server-written base directory is **still** tracked.
- [ ] 2.3 Confirm nothing else changed: a caller module with a moved mtime is still stale, a
      deleted caller module is still stale and still appears in `affected_modules`,
      `--stale-module-policy error` still rejects with `module_cache_stale`, and
      `--reset-jsenv-before-exec` still reports `reason: "explicit_request"`. Verify with
      existing mocked tests plus a read of `CheckModuleStaleness`.

## 3. Mocked coverage

- [ ] 3.1 Add mocked cases for the ledger decision in the package's test surface: a
      harness-owned path read by the loader is not recorded; a caller path read in the same
      directory is recorded; a caller file whose name matches the entry prefix but sits
      outside a server-written base is recorded.
- [ ] 3.2 Add a mocked case asserting registration happens for a filesystem base URL — that
      the write site adds membership, so a future path that writes an entry without
      registering it fails instead of silently reintroducing the false positive (design
      Risk 1).
- [ ] 3.3 Run the documented default suite and verify `OK` with no new failures.

## 4. Prove it on real hosts

- [ ] 4.1 Add a real-host case to `tests/test_real_host_integration.py` in the existing
      shared-device class: two successive execs using the same filesystem
      `--import-base-url`, with inline code that stores a marker on `ctx.globals` and reads it
      back. Assert the marker survives and the second response carries **no** `recovery`
      block. Verify the case **fails** before the fix and passes after it — that is the only
      evidence the change does anything.
- [ ] 4.2 Assert the control direction in the same class or an adjacent case: modify a
      caller-owned module in the base directory between two execs and verify it **is**
      reported stale, so the exclusion did not quietly widen into "nothing in a base
      directory is tracked".
- [ ] 4.3 Run both against the 2.2.2 host and a 3.0.0 host (clearing and restoring the 3.0.0
      host's embedded shadow with the repository-owned operations). Record payloads, the
      Editor launch count, and confirm each host's `git status --short` is empty after
      restore.
- [ ] 4.4 Re-run the two cases added by the archived
      `cover-import-and-reset-jsenv-real-host` change on both hosts and confirm they still
      pass, so this change does not weaken the reset case's discrimination.

## 5. Documentation and closeout

- [ ] 5.1 Update `openspec/specs/validation-host-integration/how-to-run.md` if any documented
      statement about stale-module policy or import base URLs is now incomplete. Verify by
      grepping the doc for `stale-module-policy` and `import-base-url` and confirming each
      statement is still true.
- [ ] 5.2 Run `openspec validate exclude-harness-entry-from-staleness --strict` and verify it
      passes.
- [ ] 5.3 Record the evidence in the change directory: before/after payloads for 4.1, the
      stale-positive result for 4.2, both hosts' runs for 4.3, and the regression run for 4.4.
- [ ] 5.4 Write the closeout finding summary stating either `No new follow-up work
      identified` or `New follow-up candidates identified`, with categories.

## Workflow follow-up

- Archive with `openspec archive exclude-harness-entry-from-staleness` once review
  requirements are satisfied, then verify `openspec/specs/cache-staleness-detection/spec.md`
  and `openspec/specs/exec-import-support/spec.md` carry the amended requirements.
- Do not absorb the HTTP `--import-base-url` coverage gap into this change; it is a separate
  follow-up already recorded by `cover-import-and-reset-jsenv-real-host`.
