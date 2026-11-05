# Tasks

## 1. Clear and restore operations

- [x] 1.1 Add the paired flags to `tools/prepare_validation_host.py` — one to clear an embedded
      shadow, one to restore it — reusing the existing shadowing detection so both act on every
      directory it names, not only the first. Verify: `python tools/prepare_validation_host.py --help`
      lists both, and the mocked cases from 2.1 pass.
- [x] 1.2 Implement clear as a filesystem move of each shadowing `Packages/` child into
      `<host root>/.unity-puer-exec-embedded-backup/<directory name>-<YYYYMMDD>/`, refusing with a
      named reason when that backup path already holds content, and never deleting. Verify: the
      mocked cases from 2.1 and 2.3 pass.
- [x] 1.3 Implement restore as the exact inverse driven by what the backup actually holds, refusing
      with a named reason when the corresponding `Packages/` child already exists rather than merging
      or overwriting. Verify: the mocked cases from 2.2 and 2.3 pass.
- [x] 1.4 Gate both directions on host freedom decided from project-local state alone — the host's
      Unity lockfile and its Editor-published endpoint — refusing with the evidence named and never
      stopping an Editor process. Verify: the mocked case from 2.4 passes.
- [x] 1.5 Extend the report envelope with `backup_path` and `reason`, add the `cleared`, `restored`,
      and `refused` status values, keep `updated` / `unchanged` / `dry-run` meanings unchanged, and
      report the post-operation `embedded_package_shadowing` value. Verify: the mocked case from 2.5
      passes and `python -m unittest tests.test_prepare_validation_host_tool` passes.
- [x] 1.6 Honour the existing preview flag for both operations, reporting the intended moves and the
      backup path without writing. Verify: the mocked case from 2.5 passes.

## 2. Mocked coverage

- [x] 2.1 Add cases for clear: every detected shadowing directory moves, the backup path is the dated
      host-local one, an occupied backup path refuses and names itself, and a host with no shadow
      reports unchanged having written nothing. Verify:
      `python -m unittest tests.test_prepare_validation_host_tool` passes.
- [x] 2.2 Add cases for restore: the backup's contents move back to their original `Packages/` paths,
      an occupied restore target refuses and names itself, and a host already carrying its embedded
      package reports unchanged. Verify: `python -m unittest tests.test_prepare_validation_host_tool`
      passes.
- [x] 2.3 Add a round-trip case asserting a clear followed by a restore reproduces the original
      `Packages/` tree byte for byte and deletes nothing. Verify:
      `python -m unittest tests.test_prepare_validation_host_tool` passes.
- [x] 2.4 Add a case asserting both directions refuse on a held lockfile or a published endpoint,
      name the evidence, move nothing, and do not attempt to stop a process. Verify:
      `python -m unittest tests.test_prepare_validation_host_tool` passes.
- [x] 2.5 Add a case pinning the report shape for every status value, including that the existing
      fields keep their meanings so current consumers are unaffected. Verify:
      `python -m unittest tests.test_prepare_validation_host_tool` passes.
- [x] 2.6 Run the default mocked suite as documented in
      `openspec/specs/validation-host-integration/how-to-run.md`. Verify: every listed module passes
      with no new failure or skip.

## 3. Documentation

- [x] 3.1 Update the shadowing section of
      `openspec/specs/validation-host-integration/how-to-run.md` to name the clear and restore
      operations, state that the pair leaves the host's version-control status as it was found, and
      state that both refuse while the host project is not free. Keep the existing statement that
      renaming a directory does not clear the shadow. Verify: the section reads as one sequence
      rather than a warning plus a hand-rolled recipe, and
      `python -m unittest tests.test_openspec_spec_hygiene` passes.
- [x] 3.2 Confirm the release-time section still holds: it reasons about the loaded copy's declared
      version, not about how the copy got there, so a cleared shadow does not change its rules.
      Verify: `openspec/specs/openupm-release-pipeline/how-to-run.md` and the release-time section of
      the validation-host how-to-run need no edit, and that conclusion is recorded in the closeout.

## 4. Real-host round trip

- [ ] 4.1 Perform a clear → prepare → real-host smoke → restore round trip against the host in
      `.env`, and confirm the host's version-control status is empty afterwards and its embedded
      package content is unchanged. Verify: the transcript, including the preparation reports at each
      step and the final empty status, is captured in the closeout summary.

## Workflow follow-up

- Archive the change with `openspec archive make-embedded-shadow-switch-reproducible` once the round
  trip is recorded and the review requirements are satisfied.
- Verify the archived result: `openspec validate --all` and
  `python -m unittest tests.test_openspec_spec_hygiene`.
