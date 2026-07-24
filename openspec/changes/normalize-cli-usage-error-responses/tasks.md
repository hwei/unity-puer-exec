## 1. Parse-failure routing

- [x] 1.1 Construct the top-level and sub parsers so a parse failure raises a typed exception carrying argparse's message verbatim, instead of writing to stderr and calling `sys.exit`.
- [x] 1.2 Catch that exception in `run_cli` and route it through the existing `usage_error()` path so it shares the envelope with post-parse usage failures.
- [x] 1.3 Confirm no prose usage block is emitted alongside the structured response, and that the process still exits `2`.
- [x] 1.4 Add unit tests for unrecognized option, missing required argument, and invalid value, asserting the JSON envelope and that no Unity service was contacted.

## 2. Status and command identification

- [x] 2.1 Add the `invalid_arguments` status for parse-layer failures, keeping exit code `2`.
- [x] 2.2 Resolve the invoked command from `argv` against the known command list, and fall back to the top-level surface only when no command token is present.
- [x] 2.3 Include the resolved command and a pointer to that command's argument help in the response.
- [x] 2.4 Add unit tests covering command resolution, the no-command fallback, and that the top-level command list is not the sole content of a subcommand failure.

## 3. Near-match suggestion

- [x] 3.1 Compute near matches for a rejected option against the option strings registered on the invoked command's subparser only.
- [x] 3.2 Apply a similarity threshold and omit the suggestion when no candidate clears it.
- [x] 3.3 Add unit tests including the reported case, `--timeout-ms` on `exec` suggesting `--wait-timeout-ms`, a case where no suggestion should appear, and a case confirming another command's options are not offered.

## 4. Usage guidance entries

- [x] 4.1 Author guidance-matrix entries for `invalid_arguments` with `situation` and a `next_steps` entry pointing at the invoked command's argument help.
- [x] 4.1a Resolve the structural tension first: the existing `runtime-guidance` requirement expects the matrix to cover all commands and all documented statuses, but the matrix is keyed by `(command, status)` and `invalid_arguments` can be emitted by every command. Decide between a per-command entry for each and a documented cross-cutting fallback, then record the decision so the coverage requirement stays satisfied rather than quietly weakened.
- [x] 4.2 Author guidance-matrix entries for the post-parse usage statuses that currently have routing but no entries, confirming first which statuses are affected rather than assuming the list.
- [x] 4.3 Ensure no usage-failure guidance offers the rejected invocation back as a retry candidate.
- [x] 4.4 Add unit tests asserting guidance presence and that no retry candidate is offered.

## 5. Shell-expansion hint

- [x] 5.1 Extend `_maybe_hint_puer_prefix` to attach a shell-expansion hint when the failure is a syntax error and the submitted `--code` contains a member access immediately followed by a call.
- [x] 5.2 Restrict the new hint to `--code`, leaving `--file` and `--stdin` invocations unhinted.
- [x] 5.3 Preserve the existing bare-prefix `ReferenceError` hint unchanged.
- [x] 5.4 Add unit tests for the expansion case, an ordinary syntax error that must not be hinted, a `--file` invocation that must not be hinted, and the preserved existing hint.

## 6. Documentation

- [x] 6.1 Document `invalid_arguments` and exit code `2` as a CLI-wide usage status in the shared help surface rather than enumerating it per command.
- [x] 6.2 Verify the documented usage-status text matches the runtime behavior by exercising both a parse-level and a post-parse usage failure.

## 7. Validation and closeout

- [x] 7.1 Run the repository unit suite and confirm no regressions, paying attention to existing tests that assert prose stderr content for rejected invocations.
- [x] 7.2 Confirm exit code `2` is unchanged for every usage-failure path so exit-code-based branching is unaffected.
- [x] 7.3 Run `openspec validate normalize-cli-usage-error-responses` and confirm the change remains valid.
- [x] 7.4 Record the apply closeout finding summary, stating either `No new follow-up work identified` or `New follow-up candidates identified`.
