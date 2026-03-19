## Context

The current `exec` implementation generates an internal request id before calling the direct execution service, but that id is not a stable public contract. The caller receives usable follow-up data only when the service responds successfully, such as `status = "running"`, `log_offset`, or a script-provided `correlation_id`.

That leaves a gap around transport-layer timeout and availability failures:

- `completed` means the request was accepted and finished.
- `running` means the request was accepted and is still active.
- `not_available` or transport timeout currently does not say whether the service never accepted the request or accepted it and the client simply lost the response.

For read-only scripts that ambiguity is inconvenient. For side-effecting scripts it is dangerous because naive retry can duplicate work.

The recent help-efficiency validation showed that agents can follow the published command hierarchy more cleanly now, but it also made this contract gap easier to see. This change should treat the problem as a product contract and observability problem first, then a help problem.

## Goals / Non-Goals

**Goals:**
- Make `exec` timeout handling distinguishable enough that callers can choose between safe retry and recovery-oriented observation.
- Expose a repository-owned execution identity that is stable across the initial request and later observation.
- Publish timeout-recovery help that explains the workflow with concrete examples.

**Non-Goals:**
- Do not redesign unrelated command families.
- Do not rely only on script-authored `correlation_id` as the sole recovery mechanism.
- Do not assume agents will infer recovery semantics from raw status codes without explicit help.

## Decisions

### Decision: Introduce a public execution identity
The CLI should expose a public `exec` request identity that callers can retain even when the first response path is ambiguous. That identity should be part of the formal contract, not an internal implementation detail.

Alternative considered:
- Keep the current internal id private and rely only on script-provided `correlation_id`. Rejected because timeout ambiguity exists before a script can reliably surface its own correlation data.

### Decision: Separate acceptance ambiguity from execution result observation
The product should let callers answer two different questions:

1. Was this `exec` request accepted?
2. If it was accepted, what happened afterward?

The first question is about request identity and recovery semantics. The second is about ongoing observation, result markers, log output, or terminal status.

Alternative considered:
- Treat timeout recovery as just another log-wait workflow. Rejected because the caller first needs to know whether there is any accepted request to observe.

### Decision: Ship help and examples with the new contract
Any new execution identity or recovery workflow must be documented in top-level and per-command help, including how it relates to `correlation_id`, `log_offset`, retries, and observation commands.

Alternative considered:
- Add the runtime contract first and leave help updates for later. Rejected because the main risk is not only implementation correctness but whether callers can safely understand the semantics.

## Open Questions

- Should the public identity be called `exec_id`, `request_id`, or something else?
- Should the follow-up surface be a new command, an `exec` status query mode, or an extension of existing observation commands?
- What retry semantics can be guaranteed when the first transport response is ambiguous?

## Risks / Trade-offs

- [Contract clarity may require a new public surface] -> Accept that cost if it is the cleanest way to avoid unsafe retries.
- [Execution identity may overlap with script-level correlation_id] -> Document the distinction clearly and keep their roles separate.
- [Richer recovery semantics may complicate help] -> Counter with focused examples and a small number of explicit recovery rules.
