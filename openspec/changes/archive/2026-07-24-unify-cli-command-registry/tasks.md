## 1. Command registry

- [x] 1.1 Add a command registry declaring the twelve commands and the help group each belongs to, placed so both `unity_puer_exec_surface` and `help_surface` can import it without a cycle.
- [x] 1.2 Derive the argparse subcommand set in `build_parser` from the registry, keeping each command's argument declarations where they are.
- [x] 1.3 Derive `COMMAND_GROUPS` / `COMMANDS` in `help_surface` from the registry.
- [x] 1.4 Add a consistency test asserting that the argparse subcommand set, `COMMANDS`, the `COMMAND_HELP` key set, the `TOP_LEVEL_COMMANDS` key set, and the set of commands appearing in `GUIDANCE_MATRIX` are all the same set, with a failure message naming which table is missing which command.

## 2. Register the compile-message commands

- [x] 2.1 Add `get-compile-errors` and `get-compile-warnings` to the registry in the troubleshooting group, and add their `TOP_LEVEL_COMMANDS` summaries.
- [x] 2.2 Author `COMMAND_HELP` entries for both: quick start, arguments (`--start`, `--count`, selector rules), and the status list, sourced from the existing `compile-error-surface` and `formal-cli-contract` requirements rather than invented.
- [x] 2.3 Author `GUIDANCE_MATRIX` entries for both, covering the statuses they can actually return, including the freshness `situation` that points at `wait-for-compile` before reading messages.
- [x] 2.4 Confirm `get-compile-errors --help`, `--help-args`, and `--help-status` render and exit `0`, and the same for `get-compile-warnings`.
- [x] 2.5 Confirm both commands now appear in `unity-puer-exec --help`.
- [x] 2.6 Add tests for help rendering, top-level visibility, and guidance presence on a non-success response from each command.

## 3. Spec alignment

- [x] 3.1 Add `wait-for-compile` to the `formal-cli-contract` authoritative flat command tree.
- [x] 3.2 Replace the hardcoded command count in the `runtime-guidance` matrix-coverage requirement with coverage expressed against the command tree.
- [x] 3.3 Add a test asserting the command set named in the durable `formal-cli-contract` spec matches the registry, so the spec cannot drift from the code again.

## 4. Validation and closeout

- [x] 4.1 Run the repository unit suite and confirm no regressions, paying attention to existing help-rendering assertions that enumerate commands.
- [x] 4.2 Verify the consistency test fails as intended by temporarily removing one command from one table, then restore it.
- [x] 4.3 Run `openspec validate unify-cli-command-registry` and confirm the change remains valid.
- [x] 4.4 Confirm the `normalize-cli-usage-error-responses` proposal's input space is unchanged apart from the two help invocations this change removes from the usage-error path, and note anything that change now needs to handle differently.
- [x] 4.5 Record the apply closeout finding summary, stating either `No new follow-up work identified` or `New follow-up candidates identified`.
