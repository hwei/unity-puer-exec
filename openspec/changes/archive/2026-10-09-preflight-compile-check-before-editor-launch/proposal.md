## Why

A C# compile error in the package cannot be discovered by the real-host suite the way a
runtime failure can. While landing `surface-play-mode-compile-block`, a wrong enum name
(`error CS0103`) made `tests.test_real_host_integration` launch the validation host in
interactive mode, where Unity opened the **Safe Mode** dialog and blocked the run until a
human clicked it. The suite then failed for a reason it could not name, and the run cost a
human interruption.

Unity can be asked to compile without an interactive session: `Unity -batchMode -quit`
compiles the project, writes the compiler diagnostics to its log, and exits. A batch-mode
preflight turns a compile error into a fast, named, non-interactive failure before the
interactive Editor is launched, so the Safe Mode dialog is never reached.

The new C# health field this change's sibling added is exactly the class of change that
should be compile-checked before any real-host run.

## What Changes

- Add a repository-local preflight helper that runs the validation host under
  `Unity -batchMode -quit -nographics`, captures the log, and reports either success or the
  parsed `error CS` diagnostics with the non-zero exit.
- Call the preflight once per real-host invocation, before the first interactive launch,
  so it does not multiply the suite's launch cost.
- Skip cleanly (and let the suite proceed) when the validation host project or a Unity
  executable is unavailable, matching the existing opt-in gate.
- Keep the preflight opt-out-able for a maintainer who already compiled the package.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `validation-host-integration`: adds a requirement that a real-host run performs a
  non-interactive compile preflight before launching the interactive Editor, and fails
  with the parsed compiler diagnostics instead of reaching the Safe Mode dialog.

## Impact

- New: a `tools/` preflight helper (batch compile + diagnostic parsing).
- `tests/test_real_host_integration.py`: module/class fixture invokes the preflight once
  before launching the interactive host.
- `tests/`: unit coverage for the diagnostic parser and the skip decision.
- `openspec/specs/validation-host-integration/spec.md`: the new durable requirement.
- No product-code change; no change to the opt-in gate or to the shared-host reuse model.
