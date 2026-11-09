# Proposal

## Why

`tools/preflight_compile_check.py` parses only `error CS` diagnostics out of the batch compile
log. That makes it blind to the failure mode that `support-puerts-2x-jsenv` actually hit: the
package compiled successfully, the preflight reported `{"status": "passed", "exit_code": 0,
"diagnostics": []}`, and it had compiled **the wrong conditional branch** — a one-sided
`versionDefines` expression silently matched nothing, so a 3.0.0 host built the 2.x code path.
The only signal was three `warning CS0618: 'JsEnv' is obsolete` lines naming this package's own
source file. No gate in the repository failed.

The defect was caught by a human reading `UnityPuerExec.Editor.rsp` for a define, because that
change's tasks happened to require it. Nothing about the tooling would have caught it in any
other change. A gate that reports `passed` while the package compiles against a deprecated API
is not a neutral omission — it is an affirmative false answer, and this repository's house rule
is that a refusal or a pass must be a named answer rather than a silence.

## What Changes

- The preflight parses `warning CS` diagnostics in addition to `error CS`, and attributes a
  diagnostic to this package by its source location, so the host's own thousands of warnings
  (a single tree5 log carries many from `com.unity.render-pipelines.core` alone) stay out of the
  result.
- Package-attributable warnings are always reported in the JSON payload under a new additive
  key, whether or not they fail the run.
- Deprecation warnings attributable to the package — `CS0618` / `CS0619` — **fail** the
  preflight, with a `kind` that distinguishes them from a compile error. That is the narrow
  class which proved both silent and meaningful: it is what "you are compiling against an API
  the dependency has retired" looks like in a log.
- Other package-attributable warnings are reported and do not fail the run, with an opt-in flag
  to escalate them. Failing on every warning would make the gate hostage to whatever a future
  Unity version decides to warn about in code that compiles fine.
- The real-host suite inherits the behavior through the same preflight it already calls, so a
  wrong-branch compile stops a real-host run before it launches an interactive Editor.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `validation-host-integration`: "Real-host validation preflights package compilation before
  launching an interactive Editor" currently fails only on compilation failure. It is amended to
  also fail on package-attributable deprecation diagnostics, and a new requirement fixes the
  attribution rule and the additive payload key so the report cannot be satisfied by counting
  the host's own warnings.

## Impact

- Tooling: `tools/preflight_compile_check.py` — a warning regex alongside `_COMPILE_ERROR_RE`,
  an attribution helper, a new payload key, a new `kind` value, and an opt-in escalation flag.
- Tests: `tests/test_preflight_compile_check.py` gains cases built from the real log lines this
  change was motivated by, including the exact three `CS0618` lines from the 3.0.0 host.
- Callers: the real-host suite and `openspec/specs/validation-host-integration/how-to-run.md`
  description of the preflight output. The payload change is additive, so a caller reading
  `status` / `exit_code` / `diagnostics` is unaffected.
- Risk of new false failures on hosts whose Unity version warns differently — addressed in
  `design.md` by narrowing the fail-set to two deprecation codes and reporting the rest.
- Follow-up to `support-puerts-2x-jsenv` (archived `2026-11-06`), whose
  `validation-evidence.md` records the silent-pass run in full.
