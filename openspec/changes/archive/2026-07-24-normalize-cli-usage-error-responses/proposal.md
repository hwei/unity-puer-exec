## Why

The CLI has two classes of usage error and treats them inconsistently. Semantic usage errors — those raised after parsing, such as `--full-text` without `--indexes` — flow through `usage_error()` and produce a machine-readable JSON envelope with a specific status, on exit 2. Parse-level usage errors never reach that path: `run_cli` calls `parser.parse_args(argv)`, argparse's own `error()` writes prose to stderr and calls `sys.exit(2)` directly, bypassing the return contract and the entry point's output handling entirely.

An agent that guesses a flag therefore receives no JSON, no status to branch on, and no pointer to the correct help tier. The 2026-07-23 validation session recorded exactly this: the agent passed `--timeout-ms` to `exec`, whose real flag is `--wait-timeout-ms`, and got back the **top-level** usage block listing only the command names — not one `exec` argument, and no indication that `exec --help-args` would list them. The interview confirmed the transcript contains no `exec --help-args` call before the guess, so the response was the agent's only chance to be redirected, and it redirected nowhere.

Separately, the existing "did you mean `puer.`" hint covers the wrong half of a documented hazard. It matches `ReferenceError: $typeof is not defined`, which is what a forgotten `puer.` prefix produces. What actually happens when PowerShell expands `$typeof` inside a double-quoted `--code` value is that the token vanishes, leaving `puer.(...)`, which is a **SyntaxError** the hint does not match — and the resulting message names neither the shell nor the quoting as the cause.

## What Changes

- Route parse-level usage errors through the same machine-readable envelope as semantic usage errors, so every usage failure produces JSON with a status and exit 2 rather than prose on stderr.
- Add an `invalid_arguments` status for parse-level failures, following the existing convention of specific status strings for usage errors.
- Name the responsible command in the response and point at that command's argument help tier, replacing the current behavior where an unrecognized argument reports the top-level usage block and lists no command arguments.
- When an unrecognized option closely resembles a real option of the invoked command, include the near match in the response, so a caller that guesses `--timeout-ms` on `exec` is told about `--wait-timeout-ms`.
- Author the missing guidance-matrix entries for usage statuses. The routing to attach guidance already exists, but entries were never written, so these responses currently carry neither `next_steps` nor `situation`.
- Extend the shell-expansion hint to the case that actually occurs: when an `exec` or `wait-for-exec` failure is a syntax error and the submitted inline `--code` carries the signature of a consumed `$` (a member access immediately followed by a call, such as `puer.(`), attach a hint naming shell expansion as the likely cause. Detection reads the submitted code rather than pattern-matching generic engine syntax-error text, to avoid firing on ordinary syntax mistakes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `formal-cli-contract`: the machine-readable-JSON requirement is extended to cover parse-level usage errors; adds the `invalid_arguments` status, the responsible-command identification, the correct help-tier pointer, and the near-match suggestion.
- `runtime-guidance`: adds guidance-matrix coverage for usage statuses that currently have routing but no authored entries, and extends the `puer.` prefix hint to the shell-expansion syntax-error case.

## Impact

- `cli/python/unity_puer_exec_surface.py`: parser construction so parse failures raise rather than exit the process.
- `cli/python/unity_puer_exec_runtime.py`: `run_cli` parse-failure handling, `invalid_arguments` payload construction, near-match computation, and the extended shell-expansion hint in `_maybe_hint_puer_prefix`.
- `cli/python/help_surface.py`: guidance-matrix entries for usage statuses; `--help-status` text for `invalid_arguments`.
- `tests/test_unity_session_cli.py`: coverage for parse-failure envelopes, command identification, near-match suggestions, and the extended hint.
- Callers currently parsing the prose usage block from stderr on exit 2 will receive JSON instead. Exit code 2 is unchanged, so exit-code-based branching is unaffected.
