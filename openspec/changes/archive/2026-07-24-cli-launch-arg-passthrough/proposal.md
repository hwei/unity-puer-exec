## Why

`launch_unity` only knows three things about a launch: the project path, the Unity
executable, and an optional log path. After `let-editor-publish-session-endpoint`,
CLI-driven launch is the primary supported path for a controllable Editor — and it
always passes the activation switch plus a project-private `-logFile`. That is
enough for most projects, but not all.

The validation host used by this repository needs `-force-gles30` to start
interactively. The host's own `exec` auto-launch fails with `unity_start_failed`
because there is no way to pass that argument through. The gap predates the
endpoint change (see its design R6 follow-up), but the endpoint change raised the
stakes: Hub-attach is no longer a silent fallback, so a project that needs an
extra Unity switch cannot be driven by the CLI at all until someone launches it
by hand with the right args.

Real-host suite task 8.7 of `let-editor-publish-session-endpoint` is blocked on
exactly this. The suite relies on CLI auto-launch; without passthrough it cannot
bring the host up.

## What Changes

- Project-scoped launch-owning commands SHALL accept a repeatable
  `--unity-launch-arg <token>` that is forwarded, as argv tokens, to the Unity
  process when **this CLI** launches the Editor.
- An ambient environment variable `UNITY_PUER_EXEC_UNITY_LAUNCH_ARGS` (JSON array
  of strings) SHALL supply the same tokens without a per-command flag, so a
  validation host or CI job can set the requirement once in `.env`.
- `launch_unity` SHALL append those tokens after the CLI-owned arguments
  (`-projectPath`, activation switch, optional `-logFile`).
- Tokens that would re-bind CLI-owned switches (`-projectPath`, `-logFile`,
  `-unityPuerExecControl`) SHALL be rejected as a usage error rather than
  silently overridden or double-applied.
- Passthrough applies only on a cold launch this CLI performs. Attaching to an
  already-running Editor ignores the tokens; they are not a way to reconfigure a
  live process.
- The real-host how-to and `.env.example` SHALL document the ambient variable so
  a contributor can unblock full-suite auto-launch on a host that needs extra
  Unity switches.
- Completing this change unblocks re-running the full real-host suite for
  `let-editor-publish-session-endpoint` (its task 8.7) before that change is
  archived.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `formal-cli-contract`: project-scoped launch supports caller-supplied extra
  Unity argv tokens, with a fixed ownership rule for CLI-owned switches.
- `validation-host-integration`: real-host run instructions and suite setup can
  supply host-required Unity launch arguments through the ambient variable.

## Impact

- `cli/python/unity_session_process.py`: `launch_unity` accepts and appends
  extra argv tokens; owns conflict rejection for CLI-owned switches.
- `cli/python/unity_session.py` / `unity_puer_exec_runtime.py` /
  `unity_puer_exec_surface.py` / `help_surface.py`: thread the flag and ambient
  source into the launch path; document the option.
- `cli/python/unity_session_env.py` (or adjacent): parse the ambient JSON env.
- `.env.example` and `openspec/specs/validation-host-integration/how-to-run.md`:
  document the ambient variable for hosts that need extra switches.
- `tests/`: unit coverage for append order, conflict rejection, ambient parse,
  and "ignored on attach". Real-host confirmation is the unblocked full suite
  under `let-editor-publish-session-endpoint` 8.7, not a new suite of its own.
