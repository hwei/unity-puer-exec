## Bridge Discoverability Rerun Summary

Date: 2026-03-23
Model: `gpt-5.4-mini subagent`

## Method

- Ran a targeted help-only rerun after the bridge-guidance help changes landed.
- Ran Standard Prompt C first, then Standard Prompt A, sequentially rather than in parallel.
- Restricted discovery to the published `unity-puer-exec` help surface plus normal CLI execution against the validation host project from `.env`.
- Evaluated bridge-recognition behavior separately from compile recovery, startup continuity, and host-side fallback.

## Standard Prompt C

- Result: task success passed, autonomy passed, efficiency remained `clean`.
- Bridge-recognition result: the agent formed the intended PuerTS-style bridge model on the first pass.
- Positive signal: the agent explicitly used the new `--help-example load-and-call-csharp-type` path together with top-level and `exec` help.
- Probing result: no extra bridge-shape probing exec calls were needed before the main compile-and-call workflow converged.
- Confirmation path: verification stayed entirely inside the CLI surface through the normal refreshed `exec -> running/phase=compiling -> wait-for-exec` flow.
- Comparison to the previous durable result: Prompt C was already `clean`, but this rerun shows a stronger bridge-discoverability story because the bridge model was now discovered from a purpose-built help path instead of being inferred mostly from the editor-exit example.

## Standard Prompt A

- Result: task success passed, autonomy passed, efficiency remained `recoverable`.
- Bridge-recognition result: the agent used the new bridge-oriented help path up front and did not perform extra bridge-shape probing before the main task converged.
- Positive signal: final confirmation stayed inside the CLI surface through execution plus a follow-up verification script.
- Remaining friction: the run still needed one implementation retry after an initial scene API mismatch during scene creation.
- Interpretation: Prompt A improved on bridge discovery but did not become `clean` because one task-specific scene-editing correction was still required before convergence.
- Comparison to the previous durable result: the remaining friction moved away from bridge-shape discovery and toward scene-editing script correctness.

## Overall Assessment

- The bridge-guidance help changes improved discoverability in the intended direction.
- The new bridge-oriented help/example path was actually used during reruns rather than remaining dead documentation.
- Prompt C now demonstrates first-pass bridge recognition without exploratory probing.
- Prompt A still has recoverable friction, but the remaining issue is no longer primarily "how do I talk to Unity/C# from JS?".
- The current evidence supports keeping this change focused on help-surface bridge guidance rather than expanding into runtime or command-surface changes.

## Follow-Up Readout

- No new follow-up candidates identified.
- The remaining Prompt A friction appears task-specific and should only become new follow-up work if repeated evidence shows the same scene-editing mismatch pattern across later reruns.
