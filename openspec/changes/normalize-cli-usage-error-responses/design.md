## Context

This change carries the runtime-side error-path remainder of the 2026-07-23 agent feedback round. Its sibling changes cover version identity (`enforce-cli-version-compatibility`) and help content (`improve-exec-and-observation-help`).

The current split is visible in source. `run_cli` (`unity_puer_exec_runtime.py:332`) intercepts help flags, then calls `parser.parse_args(argv)` at line 341. Anything argparse rejects at that call never returns: argparse's `error()` prints usage plus a message to stderr and raises `SystemExit(2)`, so the failure never passes through `run_command`, never reaches `usage_error()`, and never flows through `main()`'s output handling. Failures raised *after* a successful parse do reach `usage_error()`, which emits `{"ok": false, "status": ..., "error": ...}` on exit 2 with a status specific to the failure.

Commit `ae2f479` gave `usage_error()` the ability to attach guidance, mirroring its sibling except-clauses, and explicitly scoped itself to the routing fix with no matrix entries authored. That work is complete and correct; the consequence is that usage-error responses have a guidance channel that is presently empty. Confirmed by running a semantic usage error today: the response carries `status` and `error` but neither `next_steps` nor `situation`.

The reported symptom that motivates the change is sharper than "the error is prose". Because argparse reports unrecognized extras from the **top-level** parser after the subparser has consumed what it recognized, the usage block printed is the top-level one — command names only. The invoked command's arguments are never shown, so the response is actively less useful than the equivalent semantic failure.

## Goals / Non-Goals

**Goals:**

- One envelope for every usage failure, whichever layer detects it.
- A response that identifies the command the caller was actually invoking and points at where its arguments are documented.
- A concrete redirect when the caller's guess is close to a real flag.
- Fill the guidance channel that already exists for usage statuses.
- Make the documented PowerShell hazard self-diagnosing when it occurs.

**Non-Goals:**

- Renaming or unifying timeout flags. `--wait-timeout-ms` on `exec` and `--timeout-seconds` on the wait commands measure different things on different clocks; renaming is a breaking change with its own justification burden, and the reported friction was discovery, not naming.
- Changing exit code 2 for usage failures.
- Adding help content. Help-tier placement questions belong to the sibling help change.
- Replacing argparse.

## Decisions

### D1: Parse failures raise instead of exiting

The parsers are constructed so that a parse failure raises a typed exception rather than writing to stderr and calling `sys.exit`. `run_cli` catches it and routes through the existing `usage_error()` path.

*Alternatives considered.* Catching `SystemExit` around `parse_args` was rejected: argparse has already written prose to stderr by the time it raises, so the output would be duplicated and the structured message would arrive second. Switching to `parse_known_args` and validating leftovers manually was rejected: it silently accepts genuinely malformed input at the parse layer and moves argparse's own validation responsibilities into repository code.

### D2: The responsible command is resolved from argv, not from the parser that raised

The top-level parser is the one that reports unrecognized extras, so the raising parser does not identify the command. The command token is resolved from `argv` by matching against the known command list — the same list the subparsers are built from — which is reliable because the command is a required positional that appears before its options.

*Consequence.* When no recognizable command token is present, the failure genuinely is a top-level one, and reporting the top-level surface is then correct rather than a fallback.

### D3: `invalid_arguments` is a new status, not a reuse of `failed`

The repository already assigns specific status strings to usage failures, such as `full_text_requires_include` and `address_conflict`. A parse-level failure is a distinct, branchable condition, and collapsing it into `failed` would conflict with `failed`'s meaning of an unexpected execution failure at exit 1. The exit code stays 2, so nothing about exit-code branching changes.

### D4: Near matches are computed against the invoked command's own options

The suggestion is drawn from the option strings registered on the subparser for the resolved command, not from a global option list, so `exec` suggests `--wait-timeout-ms` rather than the `--timeout-seconds` that belongs to the wait commands. When no candidate is close enough, no suggestion is emitted; a wrong suggestion is worse than none, because it sends the caller to a flag that will fail differently.

### D5: The shell-expansion hint reads the submitted code, not the engine's error text

Matching the engine's message is unworkable here: an expanded `$typeof` leaves `puer.(...)`, whose syntax error is indistinguishable in text from any other misplaced parenthesis, so a text match would fire on ordinary mistakes. Instead the hint requires two conditions together — the failure is a syntax error, and the submitted inline `--code` contains the expansion signature of a member access immediately followed by a call. Both conditions are cheap, and requiring both keeps the false-positive rate low enough for a hint that asserts a specific cause.

*Scope.* The hint applies to `--code` only. `--file` and `--stdin` do not pass through shell interpolation, so the hazard does not arise there and a hint would be misleading.

### D6: Guidance for usage statuses points at help, not at a retry

The correct follow-up for a usage failure is to read the argument help for the resolved command, not to re-run. Matrix entries therefore carry a `situation` naming what was rejected and `next_steps` pointing at that command's `--help-args`, and do not offer the failed invocation back to the caller.

## Risks / Trade-offs

- **Prose usage output on stderr disappears for parse failures.** → A caller scraping that text would break. Mitigation: exit code 2 is unchanged, the structured response carries strictly more information than the prose did, and the prose block being replaced is the unhelpful top-level one. The behavior change is stated in the proposal.
- **Argparse behavior is being redirected rather than replaced.** → Future argparse changes to error formatting could surface unexpectedly. Mitigation: the typed exception carries argparse's message verbatim into the `error` field, so formatting changes affect message text rather than response structure.
- **A near-match suggestion can be confidently wrong.** → Mitigation per D4: candidates come from the invoked command's own options, and no suggestion is emitted below the similarity threshold.
- **The shell-expansion hint asserts a cause it infers.** → Mitigation per D5: two independent conditions must hold, and the hint is phrased as a likely cause attached to `situation` rather than as the reported error.
- **Adding a status touches every command's documented status list.** → `invalid_arguments` applies uniformly rather than per-command, so it is documented once in the shared usage-error section rather than enumerated separately for each command.
