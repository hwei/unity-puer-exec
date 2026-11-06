# Design

## Context

See `proposal.md` — Why. Current state that shapes the approach:

- `tools/preflight_compile_check.py` already does the hard part. `_COMPILE_ERROR_RE` matches
  `\berror\s+(?P<code>CS\d+)\s*:\s*(?P<message>.*)$`, `_LOCATION_RE` parses the
  `file(line,column):` prefix that precedes it, and `parse_compile_errors` returns one dict per
  line with `code`, `message`, `file`, `line`, `column`. A warning parser needs the same
  location handling, so the shape to extend already exists.
- The observed log lines are absolute and point into the repository, because the host was wired
  with a `file:` manifest entry:
  `F:\C3\unity-puer-exec-workspace\unity-puer-exec\packages\com.txcombo.unity-puer-exec\Editor\UnityPuerExecServer.cs(181,24): warning CS0618: ...`
  An embedded-copy wiring instead yields a path under the host's own `Packages/` directory, so
  attribution cannot assume the repository root.
- Host logs are noisy. A single 3.0.0 host log carried many `CS0618` warnings from
  `com.unity.render-pipelines.core` and other packages. Counting warnings without attribution
  would make the gate unusable on the first run.
- The result payload is consumed by the real-host suite and documented in
  `openspec/specs/validation-host-integration/how-to-run.md`. `status`, `kind`, `reason`,
  `exit_code`, `log_path`, `diagnostics`, `project_path`, `unity_exe_path` are all live keys.
- Both current hosts produce **zero** package-attributable warnings on the final
  `support-puerts-2x-jsenv` revision, so the gate can be turned on without first cleaning
  anything up.

## Goals / Non-Goals

**Goals:**

- A wrong-branch or deprecated-API compile stops the preflight, and says which line and which
  code, instead of reporting `passed`.
- Attribution is by the diagnostic's own source location, so host and third-party noise can
  never satisfy or trip the gate.
- The payload change is additive. No existing caller changes meaning, and no key is removed or
  repurposed.

**Non-Goals:**

- Failing on every warning. The gate owns one narrow, high-signal class by default.
- Analyzing which conditional branch compiled. That is a `versionDefines` question the preflight
  cannot answer from a log; `support-puerts-2x-jsenv` handles it by requiring a response-file
  check in its own tasks. This change makes the *symptom* loud, it does not replace that check.
- Warning policy for the host project's own assemblies.

## Decisions

### D1: One severity-aware diagnostic regex, not a second parser

Extend the existing pattern to capture severity, so `parse_compile_errors` and a new
`parse_package_warnings` share `_LOCATION_RE` and the same dict shape, differing only by which
severities they keep. Two independent regexes would duplicate the location logic that is
already subtle enough to have its own comment.

### D2: Attribution matches the package path component, not an absolute prefix

A diagnostic belongs to this package when its normalized `file` contains the path component
`com.txcombo.unity-puer-exec` under a `packages` or `Packages` directory. Normalizing means
unifying `\` and `/` and lower-casing the directory-name comparison on Windows, where the log
mixes both separators.

*Why not an absolute-prefix match against the repository root*: it works for the `file:` wiring
and silently returns nothing for an embedded host copy, which is exactly the "gate passes
because it looked in the wrong place" failure this change exists to remove. The spec delta makes
both wirings an explicit scenario for this reason.

*Why not match on the file name alone* (`UnityPuerExecServer.cs`): a host project is free to
have its own file with that name, and a false positive here fails someone's real-host run.

### D3: Fail on `CS0618` / `CS0619` only; report everything

The default fail-set is the two deprecation codes. Everything else attributable to the package
is reported and does not fail.

*Why not fail on all package warnings*: the set of warnings Unity emits for valid code is not
stable across editor versions, and this repository validates against whatever editor the host
has. A gate that fails on a new informational warning in code that compiles and behaves
correctly would be turned off, and then it protects nothing.

*Why deprecation specifically*: it is the class that was silent and load-bearing. "This symbol
exists but the dependency has retired it" is precisely what a version-conditional compile that
took the wrong branch looks like, and it is not a warning that appears and disappears with
editor patch releases.

*Alternative considered — report-only, no failure*: rejected. The motivating run reported
`passed` with `diagnostics: []`; a caller that has to remember to read a second key will not,
and the false `passed` is the actual defect.

### D4: Additive payload key and a distinct `kind`

New key `package_warnings`, holding the same dict shape as `diagnostics`. `diagnostics` keeps
its current meaning — `error CS` only — so no consumer's interpretation changes. When a
deprecation diagnostic is what failed the run, `kind` carries a new value distinguishing it
from `compile_failure`, and `reason` names the count. A caller can therefore tell "did not
compile" from "compiled against something retired" without parsing messages.

### D5: Escalation is a flag, not a config file

`--strict-package-warnings` fails the run on any package-attributable warning. A flag keeps the
decision visible in the command that made it, which matters because the two hosts are invoked
by different helpers; a config file would be a third place to look when a run fails.

## Risks / Trade-offs

- **[A host starts emitting a new deprecation in our source and blocks every real-host run]**
  → That is the gate working, but it can arrive as an unrelated surprise. Mitigation: the
  failure names the code, the file, and the line, and `reason` distinguishes it from a compile
  error, so it reads as "this symbol was retired" rather than as an opaque preflight failure.
  Both hosts are run as part of this change's tasks to establish that the current tree is clean.
- **[Attribution false positive from a host directory named like the package]** → D2 requires
  the component to sit under a `packages`/`Packages` directory, and the package name is
  reverse-domain unique. A host with its own `Packages/com.txcombo.unity-puer-exec` is the
  embedded-copy case, which *should* attribute.
- **[Log lines that wrap or carry no location]** → `_LOCATION_RE` already tolerates a missing
  location and yields `file: None`. A warning with no location cannot be attributed, so it is
  dropped from `package_warnings` rather than guessed at; the log path in the payload still
  points at it.
- **[Scope creep into "analyze the log for everything"]** → Non-goal above. One narrow class,
  one additive key, one flag.

## Migration Plan

1. Extend the parser and add the attribution helper with unit tests built from the real log
   lines, including the three `CS0618` lines from the 3.0.0 host that motivated this change.
2. Add the payload key, the new `kind`, and the escalation flag. Existing keys unchanged.
3. Run the preflight against both hosts and confirm both still report `passed` with an empty
   `package_warnings`, which is the evidence that turning the gate on does not break the
   current tree.
4. Prove the gate has teeth: reintroduce the one-sided `versionDefines` expression from
   `support-puerts-2x-jsenv` in a scratch copy of the package, run the preflight against the
   3.0.0 host, and confirm it now fails naming `CS0618`. This is the exact defect, replayed.
5. Update the preflight output description in
   `openspec/specs/validation-host-integration/how-to-run.md`.

Rollback is reverting the commit; the payload is additive, so no caller is left reading a key
that stopped existing.
