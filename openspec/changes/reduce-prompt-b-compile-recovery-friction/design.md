## Context

The current CLI can complete Prompt B natively, but the run still needs an explicit recovery step after importing the generated C# script. That makes the task viable yet not clean. The next improvement should focus on making this post-write transition more deterministic rather than pretending Unity compile recovery can always disappear.

## Goals / Non-Goals

**Goals:**
- Reduce recovery ambiguity after Prompt B writes a generated C# editor script.
- Improve first-pass convergence for the write-compile-invoke sequence.
- Validate the effect through Prompt B comparison evidence.

**Non-Goals:**
- Do not rewrite Prompt B into a simpler task.
- Do not promise that Unity C# import and compile behavior can be eliminated entirely.

## Decisions

### Decision: Treat compile recovery as workflow friction, not as an automatic out-of-scope Unity fact
This change should make the recovery path cleaner or better guided, even if some compile waiting remains inherently necessary.

### Decision: Leave room for either help-surface or product behavior improvements
The implementation may end up being a workflow example, stronger `exec`/`wait-until-ready` guidance, or a modest runtime behavior change. The deciding criterion is whether a `gpt-5.4-mini subagent` Prompt B rerun requires less explicit recovery work afterward.

## Risks / Trade-offs

- [The change may only shift recovery work rather than truly reduce it] → Use Prompt B transcript comparison, not implementation intent, as the acceptance standard.
