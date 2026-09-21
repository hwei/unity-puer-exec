## Context

`diagnose-exec-missing-after-auto-refresh` changed the automatic-refresh settle budget from
the caller's `--wait-timeout-ms` to the compile-scale readiness budget. That made the help's
wait model incomplete in a way that had already misled a caller: the real-host regression
that surfaced the defect chose `WAIT_TIMEOUT_MS = 1000` for a case that triggers a refresh,
and the test class needed a `REFRESH_WAIT_TIMEOUT_MS = 300_000` constant with a comment
explaining the internal settle+resubmit loop's budget requirement.

Current help, verified:

- `--wait-timeout-ms`: "how long to wait before returning the current execution state."
- Timeout Rules: "The command may return `running` when the wait budget ends before the
  request finishes."
- Automatic refresh: "...then settles the compile cycle before running the script."
- `exec --help-status`: names the `refreshing`/`compiling` phases under the `running`
  contract, with no mention of a separate settle budget.

Nothing states that the settle is not bounded by `--wait-timeout-ms`. The durable help
requirement for the code-only trigger boundary is the precedent for making a caller-visible
help statement explicit rather than implied.

## Goals / Non-Goals

**Goals:**

- Make the two budgets distinguishable from the help alone: the per-request wait a caller
  chooses, and the compile-scale budget the CLI settles a refresh on.
- Put the statement on every surface where `exec` describes waiting, so a caller reading only
  `--help-status` does not get the incomplete model.
- Make the statement testable so it cannot be dropped silently.

**Non-Goals:**

- Adding a caller-facing knob for the settle budget (see Decision 2).
- Changing any command's timing, response shape, or exit code.
- Restating the code-only trigger boundary, which its own requirement already covers.

## Decisions

### Decision 1: State the budget's nature, not a literal number

The help SHALL say the settle runs on a compile-scale budget that is independent of
`--wait-timeout-ms`. Task 1.3 decides whether any number is named. Preferred: no literal, so
the prose cannot drift from `unity_session.DEFAULT_READY_TIMEOUT_SECONDS`; a caller who needs
the exact figure reads it from the code, and the fact that matters -- that a small
`--wait-timeout-ms` does not abandon a refresh -- is stated exactly.

### Decision 2: Documentation only in this change

`exec` has no `--settle-timeout-seconds`; `wait-for-compile` does, with the same default. A
knob for `exec` would be a behavior change with its own trade-offs (a caller could then make
the very mistake this change documents) and is out of scope. If task 1.1 finds a caller-facing
reason to want one, it is recorded as a follow-up candidate rather than folded in.

### Decision 3: Consistency with the surfaces that already name the budget

`wait-for-compile --help` documents `--settle-timeout-seconds`; the `exec` statement must not
contradict it, and the same cycle must be described the same way on both. Task 1.3 checks both
surfaces before choosing wording.

## Risks / Trade-offs

**[Prose drifts from the constant it describes]** → Mitigated by Decision 1: state the
relationship, not the number.

**[A new help line weakens an existing help assertion]** → Help-content tests assert on
strings; adding text must not remove or relax an existing guarantee. Task 2.4 requires
reviewing each touched assertion deliberately rather than deleting a failing one.
