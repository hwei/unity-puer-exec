## Context

The current product exposes two different mechanisms for long-running work:

- `exec` starts JavaScript execution and may return `running`
- `get-result` continues the outstanding job through an opaque continuation token

That model provides structured result retrieval and safe same-session continuation, but it couples the product to a package-owned job table and introduces a command that exists only to keep waiting for async completion.

The proposed direction is to treat long-running work as an observation problem rather than a result-polling problem. The script would emit correlation-aware log markers, and the CLI would wait for those markers through `wait-for-log-pattern`. This could simplify the surface and reduce package requirements, but only if the replacement contract stays sufficiently machine-usable.

## Goals / Non-Goals

**Goals:**
- Determine whether log-driven observation can replace token-driven continuation without making the formal CLI too weak for agent use.
- Determine whether correlation-aware result markers can substitute for structured continuation tokens in the common long-job case.
- Determine whether session checks should become reusable command-level guards rather than a `get-result`-specific continuity mechanism.
- Preserve a machine-usable workflow for long-running work, including clear success and failure branching.

**Non-Goals:**
- Commit in advance to deleting `get-result` before the replacement semantics are proven acceptable.
- Require every user to depend on a repository-owned runtime helper if a documented snippet is sufficient.
- Keep the existing package-owned job system merely because it already exists.

## Assumptions

- A long-running script can emit correlation-aware result markers into the Unity log in a form reliable enough for machine parsing.
- `wait-for-log-pattern` can evolve to extract matched payload content instead of only reporting that a pattern matched.
- Session matching can be expressed as a reusable command concern rather than a continuation-token-only concern.
- Some valuable long-running workloads are better modeled as milestone observation and result-marker capture than as server-side job continuation.

## Candidate Decisions

### Candidate Decision: Prefer correlation-aware log markers over continuation tokens for long-running workflows

The leading candidate is to have long-running scripts emit a result envelope into the Editor log, for example `<result-12ab...>payload</result-12ab...>`, where the correlation id is random per invocation. The CLI would then rely on `wait-for-log-pattern` to observe and extract that specific envelope.

Why this is attractive:
- Removes `get-result` as a dedicated command surface.
- Avoids forcing the package or a user-owned server to implement a job lookup API.
- Allows observation to survive session replacement if the log source remains the intended source of truth.
- Makes the async protocol more explicit in user-authored scripts instead of hiding it behind package internals.

Risks:
- The protocol becomes partly user-defined, so examples or helpers must be very clear.
- Logs are append-only text, so large payloads, escaping, and partial writes need a documented boundary.
- Concurrent jobs require unique correlation ids and careful pattern selection.

### Candidate Decision: Treat session matching as a general command guard

If session identity matters, it should not be a special rule attached only to `get-result`. A more coherent direction is for commands such as `exec` and `wait-for-log-pattern` to accept an optional expected session identity and fail when the addressed session does not match.

Why this is attractive:
- Keeps session safety independent from a single continuation mechanism.
- Lets a log-driven workflow still protect against accidentally observing the wrong live session when same-session behavior is required.
- Leaves room for workflows that intentionally do not require same-session continuity.

Open trade-off:
- Cross-session log observation is valuable for some workloads, so session checks likely need to be optional rather than mandatory on every path.

### Candidate Decision: Use helpers or examples, not a mandatory package runtime API

The repository can provide a documented snippet or helper library that generates a random correlation id, emits start/progress/result markers, and formats result payloads for extraction. That should remain an aid, not a hard dependency.

Why this is attractive:
- Reduces package coupling for users who want minimal third-party code.
- Supports users who want to implement only a thin HTTP server and their own long-job semantics.
- Keeps the product focused on transport and observation rather than owning every job lifecycle.

## Evaluation Questions

1. Can `wait-for-log-pattern` reliably return extracted payload content, not just matched text, in a way that remains formal and machine-readable?
2. Can a log-driven workflow represent success, failure, timeout, and cancellation clearly enough without falling back to ad hoc prose parsing?
3. Can correlation ids plus optional session guards prevent false matches when multiple long-running jobs log concurrently?
4. Are there important scenarios where the final structured `result` from `get-result` is materially better than a log-emitted result envelope?
5. Does deleting `/get-result` actually simplify package and CLI implementation overall, or only shift complexity into examples and user scripts?

## Risks / Trade-offs

- [We weaken the formal machine contract] -> Require explicit evaluation of extracted-result shape, failure signaling, and branchable non-success states before removing `get-result`.
- [We shift complexity into user scripts] -> Provide a helper snippet or helper library and compare the full user workflow, not only CLI LOC.
- [Concurrent log noise causes false positives] -> Require random correlation ids and test multi-job overlap behavior.
- [Cross-session observation becomes ambiguous] -> Separate optional session guards from pure observation mode and define when each is appropriate.

## Suggested Experiment Direction

1. Prototype a script pattern that emits:
   - start marker with correlation id
   - optional progress markers
   - terminal success or failure marker with payload
2. Prototype `wait-for-log-pattern` extraction for a correlation-specific terminal marker.
3. Compare the resulting UX against `exec -> get-result` for:
   - single long job
   - concurrent long jobs
   - session restart between start and observation
   - custom server implementation that does not own a job table

## Open Questions

- Should the log result protocol use XML-like tags, JSON lines with a correlation id, or another envelope that is easier to escape and parse?
- Should `exec` itself generate a correlation id and print it in the initial response, or should helper code inside the script own correlation generation?
- If a script emits structured result markers, does the CLI need a dedicated extraction mode beyond raw regex matching?
