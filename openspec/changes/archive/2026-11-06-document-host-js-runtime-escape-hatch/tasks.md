# Tasks

## 1. Correct the claim in help

- [x] 1.1 Rewrite the exec script-authoring guidance in `cli/python/help_surface.py` so it no
      longer asserts there is no supported way to reach the host application's JavaScript runtime,
      and instead names the bridge-reachable host-environment enumeration as an escape hatch
      outside this CLI's contract. **There are two sites, not one**: the Quick Start entry (was
      line 347, "There is no supported way…") and the `--help-args` Bridge Model entry (was line
      398, "do not expect to call into…"). The existing requirement's scenario covers
      `exec --help` *or* `exec --help-args`, so fixing only the first would leave the denial on a
      surface the contract names. Verify:
      `grep -c "no supported way\|do not expect to call into" cli/python/help_surface.py` returns
      `0`, and `grep -c "separate from the host application" cli/python/help_surface.py` still
      returns a non-zero count.
- [x] 1.2 State the PuerTS-major dependence of the entry point in the same guidance block, so a
      reader on 2.x is not handed a 3.x field name or the reverse. Verify by reading the
      rendered help: `python cli/python/unity_puer_exec.py exec --help` mentions that the
      enumeration entry point differs by PuerTS major without presenting one name as universal.
- [x] 1.3 Keep the surrounding guidance coherent: the shared C#/Unity object graph remains the
      *supported* route, and the escape hatch reads as an exception to a real boundary. Verify
      `exec --help` still identifies shared-object coordination plus log observation as the
      supported approach, and that no framework-specific UI technique was added (the
      `Help scopes framework-specific technique to project-local skills` requirement still holds).

## 2. Pin the corrected wording

- [x] 2.1 Add a test to `tests/test_cli_version.py` (the module that already imports
      `help_surface` and pins rendered help) asserting the rendered exec help does **not**
      contain the absolute denial and **does** present the escape hatch as outside the CLI
      contract. Verify with `python -m unittest tests.test_cli_version` and confirm the test
      fails when the old sentence is restored in a scratch copy.
- [x] 2.2 Assert the major-dependence statement is pinned by the same test, so a future edit
      cannot collapse it back to a single field name. Verify it fails against a scratch copy
      that names only one major's entry point.
- [x] 2.3 Run the mocked default suite documented in
      `openspec/specs/validation-host-integration/how-to-run.md` and verify `OK` with no new
      failures.

## 3. Closeout readiness

- [x] 3.1 Run `openspec validate document-host-js-runtime-escape-hatch --strict` and verify it
      passes.
- [x] 3.2 Verify the delta actually supersedes the live denial rather than sitting beside it.
      `openspec/specs/formal-cli-contract/spec.md` still requires that help "does not describe any
      mechanism for calling into the host application's JavaScript runtime directly" (line 1361);
      this change's MODIFIED block must reproduce that requirement's header exactly so archive
      replaces the block. Confirm with
      `openspec validate document-host-js-runtime-escape-hatch --strict`, and record that the live
      main spec is only corrected at archive time — the post-archive grep belongs to the workflow
      follow-up, not to this task. Also verify each requirement in the delta maps to a task above
      that produced evidence for it.
- [x] 3.3 Write the closeout finding summary stating either `No new follow-up work identified`
      or `New follow-up candidates identified`, and record any real-host observation used as
      `manual-check` evidence in the change directory.

## Workflow follow-up

- Archive with `openspec archive document-host-js-runtime-escape-hatch` once review
  requirements are satisfied, then verify `openspec/specs/formal-cli-contract/spec.md` carries
  both the amended and the new requirement.
- If the decision in `proposal.md` is changed from "observed escape hatch" to "supported
  capability", widen the spec delta before apply: that choice adds a PuerTS-version tracking
  obligation this change deliberately does not take on.
