## Context

Upstream: `let-editor-publish-session-endpoint` made CLI-driven launch the primary
path for a controllable Editor. Its design R6 measured that a controlled launch
publishes correct endpoint fields, but only when the host was started with the
project-required `-force-gles30` **in addition to** the CLI's own activation
switch and private `-logFile`. CLI `exec` auto-launch of that host failed with
`unity_start_failed` because `launch_unity` has no extra-arg channel.

That gap is older than the endpoint change. It is now load-bearing: Hub-attach is
no longer a silent fallback, and the real-host suite depends on CLI auto-launch.

## Goals / Non-Goals

**Goals**

- Let a caller supply additional Unity argv tokens for a launch this CLI owns.
- Support an ambient, project-machine configuration (`.env` / process env) so the
  validation host does not need every command line restated.
- Keep CLI-owned launch arguments authoritative and conflict-free.
- Unblock full real-host suite auto-launch for hosts that need extra switches.

**Non-Goals**

- Reconfiguring an already-running Editor. Launch args bind at process start.
- A general Unity "player build args" or batch-mode scripting surface. This is
  only the interactive/project-scoped Editor launch path.
- Inventing per-project config files beyond `.env` / process env. One ambient
  channel is enough for the validation host; a later change can add project-local
  config if a second consumer appears.
- Passing args through `EditorApplication.OpenProject` / the Restart menu. That
  path already hard-codes the activation switch and isolated log; host-specific
  GLES flags for a human-driven restart are out of scope here.

## Decisions

### D1: Two input channels, one merge point

| Channel | Shape | Use |
|---|---|---|
| CLI flag `--unity-launch-arg <token>` | repeatable; each occurrence is one argv token | per-invocation override / scripting |
| Env `UNITY_PUER_EXEC_UNITY_LAUNCH_ARGS` | JSON array of strings, e.g. `["-force-gles30"]` | ambient for `.env`, CI, real-host suite |

Both feed `launch_unity`. Merge order: ambient first, then CLI flags, so an
explicit flag can extend (not replace) the ambient set. Deduplicate exact
token matches to keep a repeated `-force-gles30` from the suite and a flag
harmless.

*Rationale for JSON array rather than a shell string.* Tokenization of a free
string is locale- and shell-dependent; a JSON array is unambiguous on Windows
and in `.env` files, and matches how `--script-args` already treats structured
input at the CLI boundary.

### D2: CLI-owned switches stay CLI-owned

These tokens are rejected (usage error) if they appear in either channel, case
insensitive, with or without a following value token that would rebind them:

- `-projectPath` / `-projectpath`
- `-logFile` / `-logfile`
- `-unityPuerExecControl`

The CLI always supplies those itself on a launch it owns. Letting a caller
double-set them would either no-op confusingly or silently change isolation /
activation guarantees.

Other Unity switches (`-force-gles30`, `-force-d3d11`, `-disable-assembly-updater`,
…) pass through unchanged. The trust boundary is the same as choosing
`--unity-exe-path` and `--project-path`: the caller already controls what binary
opens which project.

### D3: Append after CLI-owned args; only on cold launch

```
Unity.exe -projectPath <proj> -unityPuerExecControl -logFile <path> [extra...]
```

Extra tokens are appended. They have no effect when the CLI attaches to an
already-running Editor — the launch path is simply not taken. Commands MUST NOT
fail solely because passthrough tokens were supplied on an attach path; the
tokens are launch-scoped, not request-scoped.

### D4: Real-host suite consumes the ambient channel

`tests/test_real_host_integration.py` does not need per-case flag plumbing. A
contributor sets in `.env`:

```
UNITY_PUER_EXEC_UNITY_LAUNCH_ARGS=["-force-gles30"]
```

`launch_unity` reads it on every cold launch. The how-to-run documents the
variable next to `UNITY_PROJECT_PATH`. Completing this change is what lets
`let-editor-publish-session-endpoint` task 8.7 run the full suite.

## Risks / Trade-offs

- **Arbitrary Unity switches can change Editor behavior substantially.** Accepted
  under the existing trust boundary of choosing the executable and project; the
  conflict list protects only the CLI's own isolation/activation contracts.
- **Ambient env applies to every launch from that process environment.** A
  developer with the validation-host `.env` loaded will also pass those args to
  other projects launched from the same shell. Documented; prefer the CLI flag
  when the ambient set is wrong for a one-off.
- **JSON in `.env` is slightly awkward to type.** Preferable to ambiguous
  shell-string splitting; `.env.example` carries a copy-pasteable value.

## Open Questions

- None that block apply. If a second consumer needs project-local config beyond
  `.env`, open a follow-up rather than expanding this change.
