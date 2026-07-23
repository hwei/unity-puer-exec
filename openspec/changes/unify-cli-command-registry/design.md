## Context

The three lists as they stand:

```
argparse subparsers (12)    formal-cli-contract              help_surface.COMMANDS (10)
                            "flat command tree" (11)
────────────────────────    ─────────────────────────        ──────────────────────────
exec                        exec                             exec
wait-for-exec               wait-for-exec                    wait-for-exec
wait-for-result-marker      wait-for-result-marker           wait-for-result-marker
wait-for-log-pattern        wait-for-log-pattern             wait-for-log-pattern
wait-for-compile            ✗ missing                        wait-for-compile
get-log-source              get-log-source                   get-log-source
get-log-briefs              get-log-briefs                   get-log-briefs
get-blocker-state           get-blocker-state                get-blocker-state
resolve-blocker             resolve-blocker                  resolve-blocker
ensure-stopped              ensure-stopped                   ensure-stopped
get-compile-errors          get-compile-errors               ✗ missing
get-compile-warnings        get-compile-warnings             ✗ missing
```

`COMMANDS` is not merely a documentation list. `handle_command_help` gates on membership, so a command absent from it cannot answer any help tier; `build_next_steps` and `build_situation` key on `(command, status)`, so a command absent from `GUIDANCE_MATRIX` silently returns no guidance for every status it can produce. Absence from `COMMANDS` is therefore a behavior change, not a documentation gap — which is why it went unnoticed: nothing fails, the responses are simply thinner.

`get-compile-errors` and `get-compile-warnings` are not experimental. They have requirements in `compile-error-surface` ("CLI exposes get-compile-errors and get-compile-warnings commands") and in `formal-cli-contract` (two dedicated command requirements). The specs treat them as first-class; only the help surface does not.

## Goals / Non-Goals

**Goals:**

- One declaration of the command set, with the other four consumers derived from or checked against it.
- The two compile commands documented and guided on the same terms as every other command.
- Specs that describe the registry structurally instead of restating its contents or its size.
- A test that turns "added a command and forgot a table" from a silent thinning of responses into a failure.

**Non-Goals:**

- Changing what any command does, its arguments, its statuses, or its exit codes.
- Reworking the guidance matrix's `(command, status)` key. That keying tension is recorded against `normalize-cli-usage-error-responses` and is not reopened here.
- Authoring rich workflow guidance for the compile commands beyond what their statuses require. Content quality is a separate concern from registration.
- Adding, removing, or renaming any command.

## Decisions

### D1: The registry declares command identity; the tables stay separate

The registry names the command set and the group each command belongs to. It does not absorb `COMMAND_HELP` bodies, argparse argument declarations, or `GUIDANCE_MATRIX` entries — those stay where they are, keyed by command name.

*Rationale.* The drift was in *membership*, not in content. Collapsing four differently-shaped tables into one structure would be a large refactor of working code to fix a problem that only concerns which keys exist. Keeping the tables and unifying their key set is the smaller change with the same effect.

*Alternative considered.* A single declarative table holding parser arguments, help text, and guidance per command was rejected: it would rewrite roughly 1400 lines of `help_surface.py` and the whole of `build_parser` for no behavioral gain, and would make the diff impossible to review against the current content.

### D2: Consistency is enforced by test, not by construction alone

`build_parser` derives its subcommand set from the registry, but `COMMAND_HELP` and `GUIDANCE_MATRIX` are literal dictionaries whose *content* must be authored per command. A test asserts that all four key sets equal the registry.

*Rationale.* Deriving keys mechanically from the registry would let an unwritten entry produce an empty help page rather than a failure — the same silent thinning that hid this bug. A missing entry should be loud. The test is the enforcement point precisely because content cannot be generated.

*Consequence that matters.* Adding a command becomes a five-place edit that fails until complete, instead of a one-place edit that quietly degrades responses.

### D3: Specs describe the registry structurally

`runtime-guidance` currently says the matrix "SHALL cover all ten commands". The count is restated as coverage of every command in the authoritative tree. `formal-cli-contract` keeps enumerating the tree — that enumeration *is* the authoritative declaration, and it gains `wait-for-compile`.

*Rationale.* One spec should own the list; others should reference it. Two specs independently restating the same set, one of them as a number, is how the discrepancy survived.

### D4: The compile commands' guidance is authored from their real statuses

Both commands contact the control service, so they can return `not_available`, `unity_not_ready`, `version_mismatch`, and the usage statuses, plus a `compiling` state. Their guidance is written from that set, including a `situation` that names the freshness hazard `wait-for-compile` exists to defeat — reading compile messages before a triggered compile has settled returns the previous compilation's results.

*Rationale.* Registering the commands without authoring their entries would satisfy the consistency test with empty dictionaries and leave the original complaint — no `next_steps`, no `situation` — unaddressed.

### D5: Land before `normalize-cli-usage-error-responses`

Both changes modify the path where `handle_command_help` returns `None` and control falls through to argparse.

*Rationale.* Today `get-compile-errors --help` reaches that path and produces "unrecognized arguments: --help", which is a misdiagnosis — `--help` is valid, the command is simply unregistered. If `normalize-cli-usage-error-responses` lands first, it will carefully wrap that misdiagnosis in a JSON envelope with a near-match suggestion, and this change then deletes the case. Landing this first shrinks the input space that change has to handle.

## Risks / Trade-offs

- **A caller depending on `get-compile-errors --help` exiting 2 breaks.** → Marked BREAKING. The prior behavior was a defect, and no documented workflow depends on a help request failing.
- **The consistency test will fail the next time a command is added.** → That is the intent. The failure message should name the missing table so the fix is obvious rather than a hunt.
- **Authoring help and guidance content for two commands is judgment work, not mechanical.** → Bounded: their arguments (`--start`, `--count`, selectors) and statuses are already specified in `compile-error-surface` and `formal-cli-contract`, so the content has a source rather than being invented.
- **Two spec files change to remove one number.** → Small, but it is the change that stops the drift from recurring; leaving the count in place would preserve the exact mechanism that hid this.
