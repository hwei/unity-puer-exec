# Tasks

## 1. Version-conditional Editor assembly

- [x] 1.1 Add the `versionDefines` entry to `packages/com.txcombo.unity-puer-exec/Editor/UnityPuerExec.Editor.asmdef`
      (`com.tencent.puerts.core`, expression `[3.0.0`, define `PUERTS_3`), and verify the file is still valid JSON
      with the existing `references` entry unchanged: `python -c "import json;json.load(open('packages/com.txcombo.unity-puer-exec/Editor/UnityPuerExec.Editor.asmdef'))"`.
- [x] 1.2 Split the `jsEnv` field declaration in `Editor/UnityPuerExecServer.cs` on `#if PUERTS_3` (`ScriptEnv` on
      3.x, `JsEnv` on 2.x), and verify by inspection that every remaining `jsEnv` reference (`ExecuteModule`,
      `Tick`, `Dispose`, null checks) is outside any conditional block:
      `grep -n "jsEnv" packages/com.txcombo.unity-puer-exec/Editor/UnityPuerExecServer.cs`.
- [x] 1.3 Move `JsBackendTypeNames` and `CreateScriptEnv` into the `#if PUERTS_3` branch unchanged, add the 2.x
      `CreateScriptEnv(ILoader loader) => new JsEnv(loader)` counterpart, and verify no `ScriptEnv` or `Backend`
      identifier remains outside a 3.x conditional:
      `grep -n "ScriptEnv\|Backend" packages/com.txcombo.unity-puer-exec/Editor/UnityPuerExecServer.cs`.
- [x] 1.4 Lower the dependency in `packages/com.txcombo.unity-puer-exec/package.json` from `3.0.0` to `2.2.2` and
      update the pin in `tests/test_package_layout.py` in the same edit, then verify
      `python -m unittest tests.test_package_layout` passes.

## 2. Repository-level tests

- [x] 2.1 Add a source-invariant test asserting the two branches are mutually exclusive and complete — the asmdef
      carries exactly one `versionDefines` entry keyed to `com.tencent.puerts.core` defining `PUERTS_3`, and every
      `ScriptEnv`/`Backend` reference in `UnityPuerExecServer.cs` sits inside an `#if PUERTS_3` region while a
      `JsEnv` construction sits inside the matching `#else` — so a later edit that drops the guard fails the
      default suite. Verify with `python -m unittest tests.test_puerts_version_compat` (new module) and confirm
      it fails when a guard is deliberately removed in a scratch copy.
- [x] 2.2 Run the mocked default suite listed in `openspec/specs/validation-host-integration/how-to-run.md` and
      verify `OK` with no new failures, plus the new module from 2.1 included in that documented command line.

## 3. 2.x host validation (`c3-client-tree2`, `com.tencent.puerts.core` 2.2.2)

- [x] 3.1 Wire the host with `python tools/prepare_validation_host.py --dry-run` then without `--dry-run`, and
      verify `Project/Packages/manifest.json` gains the `file:` entry for `com.txcombo.unity-puer-exec` plus the
      `testables` declaration, and that the host's `com.tencent.puerts.core` still reports `2.2.2`.
- [x] 3.2 Run `python tools/preflight_compile_check.py` against that host and verify `status: passed`,
      `exit_code: 0`, that the batch log contains no `error CS0246` naming `ScriptEnv` (issue #4's symptom)
      and no `CS0618` obsolete-`JsEnv` warning, and — because a `passed` preflight does not by itself prove
      which branch compiled, and Bee short-circuits an assembly it considers up to date — that the log shows a
      real `Csc .../UnityPuerExec.Editor.dll` and that `PUERTS_3` is **absent** from `UnityPuerExec.Editor.rsp`.
- [x] 3.3 Run `python tools/run_editmode_tests.py` against that host and verify `status: passed` with the same
      test count as the 3.x baseline, so the EditMode assembly is not silently skipping on 2.x.
- [x] 3.4 Launch the host Editor with the control argument and verify end to end against the live 2.2.2 host:
      `exec` with an inline body reaches a terminal `completed`; `exec --import-base-url` resolves a relative
      import; `exec --reset-jsenv-before-exec` reloads a module changed between two runs; `play` then `stop`
      both reach terminal states. Record the responses as the change's host-validation evidence.
- [x] 3.5 If 3.4 shows module resolution failing on 2.x, add `IModuleChecker` to `PuerExecLoader` under the same
      `#if` split (design.md, Risks) and repeat 3.2–3.4; otherwise record in the change that the risk did not
      materialize.

## 4. 3.x regression (`c3-client-tree5`, `com.tencent.puerts.core` 3.0.0)

- [x] 4.1 Clear the host's embedded 0.12.0 shadow with
      `python tools/prepare_validation_host.py --clear-embedded-shadow --project-path F:/C3/c3-client-tree5/Project`
      and then wire it, verifying the tool reports the moved directory under `.unity-puer-exec-embedded-backup/`
      and the manifest gains the `file:` entry — otherwise the tests would exercise the old shipped source.
- [x] 4.2 Run `python tools/preflight_compile_check.py --project-path F:/C3/c3-client-tree5/Project` and verify
      `status: passed`, a real `Csc .../UnityPuerExec.Editor.dll` in the log, that `PUERTS_3` **is present** in
      `UnityPuerExec.Editor.rsp`, and that no `CS0618` naming `JsEnv` appears — together the positive evidence
      that the `ScriptEnv` branch compiled. A `passed` preflight alone is not sufficient: the first attempt
      reported `passed` with `diagnostics: []` while silently compiling the 2.x branch, because the one-sided
      `[3.0.0` expression matched nothing and the tool parses only `error CS`.
- [x] 4.3 Run `python tools/run_editmode_tests.py --project-path F:/C3/c3-client-tree5/Project` and verify the
      passed count matches the pre-change 3.x baseline of 21.
- [x] 4.4 Run one `exec` and one `play`/`stop` cycle against the 3.x host and verify terminal statuses, then
      restore the host with `--restore-embedded-shadow` and `--restore-manifest` and verify
      `git -C F:/C3/c3-client-tree5 status --short` is clean.

## 5. Integration and closeout readiness

- [x] 5.1 Run `openspec validate support-puerts-2x-jsenv --strict` and verify it passes with no description-length
      or missing-scenario warnings.
- [x] 5.2 Verify the two durable specs agree with the shipped package after a hypothetical archive: the
      `openupm-release-pipeline` delta's `2.2.2` floor matches `package.json`, and the new
      `puerts-version-compatibility` spec's requirements each map to a task above that produced evidence for them.
- [x] 5.3 Write the closeout finding summary stating either `No new follow-up work identified` or
      `New follow-up candidates identified`, listing the issue #4 side-note documentation change as a named
      follow-up candidate under `product-improvement`, and record the evidence table (mocked suite, 2.x
      preflight/EditMode/exec, 3.x preflight/EditMode/exec) in the change directory.
- [ ] 5.4 Post the resolution to GitHub issue #4 — the version-detection mechanism, the corrected finding that
      2.2.2 does contain `Backend*` and lacks only `ScriptEnv`, the evidence table, and the release that will
      carry it — and verify the comment renders the table. Leave the issue open until that release exists, as
      issue #3 does.

## Workflow follow-up

- After the release that carries this change is cut, close issue #4 and issue #3 together, naming the released
  version in both.
- Create the follow-up change for the `jsEnvs` / `Eval` host-runtime escape hatch documentation (issue #4's side
  note). It applies to both PuerTS majors — `Puerts.JsEnv.jsEnvs` on 2.x (`Runtime/Src/Default/JsEnv.cs:26`) and
  `Puerts.ScriptEnv.scriptEnvs` on 3.x — so `cli/python/help_surface.py:347` and the `runtime-guidance` spec are
  both wrong to call it unsupported without qualification.
- Archive this change with `openspec archive support-puerts-2x-jsenv` once the project's review requirements are
  satisfied, then verify the archived result and the two updated main specs.
