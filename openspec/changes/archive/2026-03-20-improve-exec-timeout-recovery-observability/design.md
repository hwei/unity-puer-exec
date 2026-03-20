## Context

The current `exec` implementation generates an internal request id before calling the direct execution service, but that id is not a stable public contract. The caller receives usable follow-up data only when the service responds successfully, such as `status = "running"`, `log_offset`, or a script-provided `correlation_id`.

That leaves a gap around transport-layer timeout and availability failures:

- `completed` means the request was accepted and finished.
- `running` means the request was accepted and is still active.
- `not_available` or transport timeout currently does not say whether the service never accepted the request or accepted it and the client simply lost the response.

For read-only scripts that ambiguity is inconvenient. For side-effecting scripts it is dangerous because naive retry can duplicate work.

The recent help-efficiency validation showed that agents can follow the published command hierarchy more cleanly now, but it also made this contract gap easier to see. This change should treat the problem as a product contract and observability problem first, then a help problem.

The current package implementation also exposes internal multi-job machinery such as `host.startJob(...)`, spawned jobs, and a server-side job dictionary. That machinery does not currently form a public CLI contract, and there is no evidence that the published help, OpenSpec requirements, or automated validations depend on it directly. The recovery design should prefer a simpler public model rather than preserving queue-like or spawned-job semantics by default.

## Goals / Non-Goals

**Goals:**
- Make `exec` timeout handling distinguishable enough that callers can choose between safe retry and recovery-oriented observation.
- Expose a repository-owned execution identity that is stable across the initial request and later observation.
- Publish timeout-recovery help that explains the workflow with concrete examples.
- Keep the public execution contract simple enough that callers do not need to reason about implicit server-side queuing or multiple concurrent top-level `exec` requests.

**Non-Goals:**
- Do not redesign unrelated command families.
- Do not rely only on script-authored `correlation_id` as the sole recovery mechanism.
- Do not assume agents will infer recovery semantics from raw status codes without explicit help.
- Do not preserve internal spawned-job or queue-like semantics unless a concrete public dependency is discovered during implementation.

## Decisions

### Decision: Introduce a caller-owned public request identity
The CLI should expose a public `request_id` for `exec`, and the caller should own that identity before the first submission. The CLI should generate a fresh `request_id` automatically for normal usage, while also allowing an explicit `--request-id` when the caller intentionally wants recovery or idempotent replay behavior. The public identity should be part of the formal contract, not an internal implementation detail.

Alternative considered:
- Keep the current internal id private and rely only on script-provided `correlation_id`. Rejected because timeout ambiguity exists before a script can reliably surface its own correlation data.

### Decision: Treat `request_id` as an idempotency key, not just a lookup token
The service should treat `request_id` as the idempotency key for top-level `exec`. Reusing the same `request_id` with an equivalent execution request should not duplicate side effects or start a second execution. Reusing an existing `request_id` with materially different execution content should fail explicitly as `request_id_conflict`.

Alternative considered:
- Generate `request_id` only after acceptance and expose it only on non-terminal responses. Rejected because callers need a stable identity before ambiguous transport failure if they are going to recover safely without guessing whether a duplicate execution happened.

### Decision: Use a single-active-request public model
The public `exec` contract should allow at most one active top-level request at a time. When a different `request_id` arrives while another top-level `exec` request is still active, the service should return `busy` rather than queueing the new request silently. This keeps the user-facing model simple and avoids making callers reason about hidden server-side scheduling.

Alternative considered:
- Preserve a public queue or multi-request model on top of the current internal job map. Rejected because the current product value is in safe execution and recovery, not in orchestrating multiple concurrent or queued top-level requests.

### Decision: Separate accepted-request recovery from script-level observation
The product should let callers answer two different questions:

1. Was this `exec` request accepted?
2. If it was accepted, what happened afterward?

The first question is about request identity and recovery semantics. The second is about ongoing observation, result markers, log output, or terminal status.

Alternative considered:
- Treat timeout recovery as just another log-wait workflow. Rejected because the caller first needs to know whether there is any accepted request to observe.

### Decision: Add a dedicated follow-up surface for accepted requests
The recommended follow-up surface should be a new `wait-for-exec --request-id ...` command. `exec` replay with the same `request_id` remains a valid idempotent recovery path, but `wait-for-exec` should be the preferred public continuation command because it does not require resending the script body and keeps recovery intent explicit.

Alternative considered:
- Rely only on idempotent `exec` replay with the same `request_id`. Rejected because a separate follow-up command is easier to explain in help and avoids making callers resubmit script content during normal recovery.

### Decision: Keep request equivalence tied to execution semantics, not CLI input form
Equivalent `exec` requests should be compared by normalized execution semantics rather than by the raw CLI form that produced them. Matching should be based on the effective target identity and normalized script content, not on whether the caller used `--file`, `--stdin`, or `--code`. Response-shaping flags such as wait budget or diagnostics toggles should not redefine the underlying execution identity.

Alternative considered:
- Treat path, stdin usage, or other CLI transport details as part of request equivalence. Rejected because callers should be able to recover the same execution intent even if the same script content is resubmitted through a different input form.

### Decision: Do not distinguish `never_seen` from `expired` in this change
The follow-up surface should use a single `missing` state when the addressed service has no recoverable record for the requested `request_id`. This change should not split that state into `never_seen` versus `expired` until the service has an explicit retention policy and durable semantics for record lifetime.

Alternative considered:
- Expose separate `never_seen` and `expired` outcomes immediately. Rejected because the current implementation does not yet define stable retention semantics, so that distinction would be more precise than the product can honestly guarantee.

### Decision: Ship help and examples with the new contract
Any new execution identity or recovery workflow must be documented in top-level and per-command help, including how it relates to `correlation_id`, `log_offset`, retries, idempotent replay, and observation commands.

Alternative considered:
- Add the runtime contract first and leave help updates for later. Rejected because the main risk is not only implementation correctness but whether callers can safely understand the semantics.

### Decision: Treat spawned-job machinery as presumptive legacy implementation
The current package-side spawned-job helpers and job graph details should not shape the new public contract. Unless apply work discovers a concrete dependency, this change should remove `host.startJob(...)`, spawned-job tracking, and other unused public-to-script hooks that imply a multi-job execution model the CLI no longer wants to expose.

Alternative considered:
- Preserve the spawned-job surface because it already exists internally. Rejected because it increases the apparent execution model complexity without supporting the timeout-recovery contract that this change is trying to define.

## Open Questions

- What exact normalized fields should count toward exec-request equivalence beyond target identity and script content?
- Should terminal request records remain queryable only until a replacement request starts, or for a short bounded retention window afterward?
- Should `busy` mean strictly `running`, or any non-terminal active request state that still owns the single exec slot?

## Risks / Trade-offs

- [Single-active-request contract may feel stricter than the current internals] -> Accept the restriction because it is simpler and safer for callers than implying hidden queue behavior.
- [Execution identity may overlap conceptually with script-level correlation_id] -> Document the distinction clearly and keep their roles separate.
- [Idempotent replay requires consistent equivalence rules] -> Counter with explicit normalization rules in the contract and tests.
- [Removing spawned-job hooks could surprise an undiscovered internal consumer] -> Verify usage during apply and only preserve it if a real dependency is found.
- [Richer recovery semantics may complicate help] -> Counter with focused examples and a small number of explicit recovery rules.
