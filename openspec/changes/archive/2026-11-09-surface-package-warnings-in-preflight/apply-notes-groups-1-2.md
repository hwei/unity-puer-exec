# Apply notes — groups 1 and 2 (tool code and unit tests)

Scope of this note: tasks 1.1–1.3 and 2.1–2.5 of `tasks.md`. Groups 3 (real-host
proof) and 4 (docs, validation, closeout) belong to another owner and were not
executed here. No Unity Editor was launched, no validation host was touched, and
`openspec/specs/validation-host-integration/how-to-run.md` was left unmodified.

Files changed:

- `tools/preflight_compile_check.py`
- `tests/test_preflight_compile_check.py`

Scratch probes live under `.tmp/` (see "Verification evidence" at the end).

## Parser (tasks 1.1 – 1.3)

`_COMPILE_ERROR_RE` is replaced by one severity-aware pattern:

```python
_DIAGNOSTIC_RE = re.compile(
    r"\b(?P<severity>error|warning)\s+(?P<code>CS\d+)\s*:\s*(?P<message>.*)$"
)
```

`_LOCATION_RE` and the returned dict shape (`code`, `message`, `file`, `line`,
`column`) are unchanged and shared by both readers. Two public readers now sit on
one private implementation, `_parse_diagnostics(log_text, severity)`:

- `parse_compile_errors(log_text)` — `error` only, so the `diagnostics` payload key
  keeps its existing meaning.
- `parse_package_warnings(log_text)` — `warning` only, filtered to package-owned
  files.

If a line happens to mention the other severity first, the reader advances past
that match instead of giving up on the line, so a requested severity is never
shadowed by an earlier rejected one. It still returns the *first* match of the
requested severity, which is what keeps `parse_compile_errors` byte-identical to
the pre-change parser.

Byte-identical verification (task 1.1): `.tmp/parse_identity_probe.py` carries a
verbatim copy of the pre-change `parse_compile_errors` and compares
`json.dumps` bytes for six fixtures — the file's `TWO_ERROR_LOG`, an error with no
source location, a clean/warning-only log, a mixed real-host-shaped log (absolute
`F:\...` package path, third-party `Packages/` path, `Library/PackageCache` path,
an `error CS9999` with no location, a mixed-severity line, and a bare warning),
plus `""` and `None`. Result: `ALL IDENTICAL`.

## Attribution rule as implemented (task 1.2)

```python
PACKAGE_NAME = "com.txcombo.unity-puer-exec"
_PACKAGE_PARENT_DIRECTORIES = frozenset({"packages"})

def is_package_source_file(file_path): ...
```

The rule, in order:

1. `None` / empty → not attributable. A diagnostic without a location is dropped
   from `package_warnings` rather than guessed at (design D-Risks); the payload's
   `log_path` still points at the log.
2. Split the path into components after replacing `\` with `/`, discarding empty
   components. This handles a log that mixes separators and leaves absolute drive
   prefixes (`F:`) as an ordinary leading component.
3. Lower-case every component. `packages` therefore matches both `packages/` and
   `Packages/`, and the package component matches case-insensitively.
4. Attribute **only** when the package-name component is immediately preceded by a
   `packages` component.

The four required shapes:

| shape | example | attributed |
|---|---|---|
| absolute repository path from a `file:` wiring | `F:\C3\...\unity-puer-exec\packages\com.txcombo.unity-puer-exec\Editor\UnityPuerExecServer.cs` | yes |
| host-relative embedded copy | `Packages/com.txcombo.unity-puer-exec/Editor/UnityPuerExecServer.cs` | yes |
| third-party package | `Packages/com.unity.render-pipelines.core/...`, `Library/PackageCache/...` | no |
| `file` is `None` | (no location prefix) | no |

Two deliberate non-matches, both asserted in the tests: the same directory name
under `Assets/` (no `packages` parent) and a host file that merely shares the
basename `UnityPuerExecServer.cs` under a different package directory. The rule
is relative, so it does not depend on the host being the repository root — which
is the point of making both wirings explicit rather than matching an absolute
prefix.

## Payload and decision (tasks 2.1 – 2.5)

New payload keys and values:

| key / value | meaning |
|---|---|
| `package_warnings` (new key) | list of package-attributable `warning CS` entries, same dict shape as `diagnostics`. Present on **every** non-skipped payload — `passed`, `compile_failure`, `package_deprecation`, `package_warning`, `launch_failure`, `timeout` — and also on the `skipped` payload as `[]`. |
| `diagnostics` (unchanged) | `error CS` only. Not repurposed, not widened to include warnings. |
| `kind = "package_deprecation"` (`KIND_PACKAGE_DEPRECATION`) | new value, distinct from `"compile_failure"`. Set when at least one `package_warnings` entry carries `CS0618` or `CS0619` and no `error CS` diagnostic was found. |
| `kind = "package_warning"` (`KIND_PACKAGE_WARNING`) | new value, set only under `--strict-package-warnings` when package warnings exist but none is a deprecation. |
| `reason` | names the count: `"... reported N package deprecation diagnostic(s) (CS0618, CS0619)"` or `"... reported N package warning(s) under --strict-package-warnings"`. |

Precedence when several signals are present: `compile_failure` (from `error CS`)
wins over deprecation, which wins over strict escalation, which wins over
`launch_failure`. That keeps the existing meaning of `compile_failure` intact and
avoids reporting a compile error as a deprecation. Strict escalation is only
considered when the batch Editor exited `0`: a non-zero exit with a package
warning and no `error CS` stays `launch_failure`, because the warning did not
cause the exit code. A deprecation diagnostic, by contrast, fails even on a zero
exit — that is the whole point, since the motivating run exited `0`.

Decision table for a log with a given content and a clean exit:

| log content | default | `--strict-package-warnings` |
|---|---|---|
| package warning `CS0618` / `CS0619` | **failed**, `package_deprecation` | failed, `package_deprecation` |
| package warning, other code | passed, `package_warnings` non-empty | **failed**, `package_warning` |
| warnings only from other packages / the host | passed, `package_warnings == []` | passed, `package_warnings == []` |

`DEPRECATION_WARNING_CODES = frozenset({"CS0618", "CS0619"})` is the whole
default fail-set; every other package-attributable warning is reported, not fatal
(design D3).

`--strict-package-warnings` is a `store_true` CLI flag forwarded to
`run_preflight(..., strict_package_warnings=False)`; it escalates *any*
package-attributable warning and, as the last table row shows, cannot be tripped
by host or third-party noise because attribution happens before the decision.

`format_failure_detail` now renders three shapes, all multi-line:

```
package compile preflight failed with 3 package deprecation warning(s) (CS0618, CS0619):
Packages/com.txcombo.unity-puer-exec/Editor/UnityPuerExecServer.cs(181,24): warning CS0618: 'JsEnv' is obsolete: 'use ScriptEnv instead'
...
```

The compile-failure rendering is unchanged (same header text, same
`file(line,column): error CODE: message` line format — the shared helper emits
identical text for `error`), so the existing detail assertions still pass
unmodified.

## Unit test coverage added

Existing test lines were not modified: `git diff -U0` on the test file shows zero
removed lines. The new coverage is additive, in three new classes plus one added case in
`ParseCompileErrorsTests`:

- `ParseCompileErrorsTests.test_one_mixed_severity_line_yields_the_error_for_the_error_parser`
- `PackageAttributionTests` — the four required shapes, plus the two
  non-matches (wrong parent directory, shared basename).
- `ParsePackageWarningsTests` — exactly three entries for the real `CS0618` log
  lines (codes, lines 181/1647/1649, columns, message, ending filename), one for
  the embedded-copy variant, zero for a log whose only warnings are third-party,
  zero for a warning with no location, and the shared entry shape.
- `PackageWarningPayloadTests` — the additive key on every non-skipped payload
  and on the skipped one; `diagnostics` still `error CS` only; deprecation failure
  carries kind/file/line/code and a count in `reason`; `CS0619` also fails; the
  embedded-copy warning fails the same way; third-party noise passes; a
  non-deprecation package warning passes with a non-empty `package_warnings`;
  the strict flag both ways on the same log; strict does not fire on host noise;
  strict does not relabel a non-zero exit as an escalation; the CLI flag parses;
  the deprecation and strict failure details name file, position, code, and
  message; `require_preflight` raises the deprecation detail.

The fixture `REAL_PACKAGE_CS0618_LOG` is transcribed from the three `CS0618` lines
in
`openspec/changes/archive/2026-11-06-support-puerts-2x-jsenv/validation-evidence.md`
(under "Finding: a one-sided `versionDefines` expression matches nothing,
silently"), reattached to the absolute repository path the `file:` wiring
produces.

## Verification evidence

Command and exact summary line:

```
python -m unittest tests.test_preflight_compile_check -v
Ran 47 tests in 0.091s
OK
```

Also run (read-only, no Editor): the documented default mocked suite in
`openspec/specs/validation-host-integration/how-to-run.md` — `Ran 877 tests in
64.463s`, `OK`.

`python tools/preflight_compile_check.py --help` lists
`--strict-package-warnings`.

## Task state

1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 2.4, 2.5 are marked `[x]` in `tasks.md`. Groups 3
and 4 remain untouched and unchecked; they require a Unity Editor and a validation
host, which are outside this session's boundaries.

## Not done here (owned by the group 3/4 owner)

- `openspec/specs/validation-host-integration/how-to-run.md` still describes only
  `status`, `exit_code`, `log_path`, `diagnostics` (task 4.1).
- No real-host run has confirmed that both hosts report `status: passed` with an
  empty `package_warnings` (tasks 3.1–3.2), and the motivating defect has not been
  replayed against a 3.0.0 host (task 3.3).
