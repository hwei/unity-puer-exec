## Context

The newly archived revalidation round confirmed that `unity-puer-exec` remains usable for the repository's baseline help-only agent workflows, but the remaining verification-closure problem is narrower than the first read suggested. Prompt A still escapes the intended CLI verification surface:

- Prompt A succeeded only after explicit startup recovery and then used direct host scene-file confirmation.

A direct manual probe performed after that revalidation established an important control case: a minimal workflow that writes a simple C# static method and then immediately issues a second `exec` to call that method succeeds without an explicit `wait-until-ready` between the two requests. That result strongly suggests the former Prompt B evidence is not the right primary baseline for this change. The old menu-and-selection task mixes at least three concerns:

- basic code-write, compile, and re-exec behavior
- log-observation guidance
- Unity Editor interaction timing around selection and menu execution

That means the current mainline problem is narrower than general usability but deeper than help wording. The repository already has contract pieces for `request_id`, `wait-for-exec`, `wait-for-log-pattern`, `wait-for-result-marker`, `log_offset`, and effective log-path handling. For this change, the design work is now centered on two primary acceptance tracks:

- Prompt A: scene editing with project-scoped startup continuity
- Standard Prompt C: basic C# compile-and-call verification

Log-observation guidance and editor-interaction timing remain real product questions, but they should be handled in their own linked follow-up changes rather than continuing to distort the main baseline.

## Goals / Non-Goals

**Goals:**
- Clarify which parts of the current verification workflow are product gaps versus agent prompt or script-authoring noise.
- Preserve a shared change for the common verification-closure problem while keeping Prompt A and Standard Prompt C as separate acceptance tracks.
- Identify whether the main gap is contract shape, help guidance, runtime observation behavior, or some combination of those.
- Land durable OpenSpec guidance that can support a later implementation change without prematurely locking the mechanism.

**Non-Goals:**
- Do not expand the task set beyond Prompt A and one cleaner baseline for basic C# compile-and-call verification.
- Do not assume the solution is only help text or only runtime changes before exploration is complete.
- Do not fold the broader project-scoped startup-reliability problem into this change unless it proves inseparable from verification closure.
- Do not treat Selection, menu execution, or delayed editor-interaction timing as the primary baseline for this change.

## Decisions

### Decision: Keep the change centered on verification closure, not all runtime friction
The revalidation evidence surfaced both startup friction and verification friction, but this change should first focus on the shared gap: agents still leave the intended CLI-native confirmation path to verify success. Startup reliability remains important, but it does not currently explain Prompt B's fallback to direct host-log inspection by itself.

Alternative considered:
- Merge startup reliability and verification closure into one broad runtime-improvement change. Rejected because it would blur diagnosis and make it harder to decide which parts of the workflow actually need contract or surface changes.

### Decision: Use Prompt A and a new Standard Prompt C as separate acceptance tracks inside one shared change
Prompt A and Standard Prompt C exercise different parts of the same user-facing promise: an agent should be able to complete a basic project-scoped workflow and confirm success through the CLI surface without host-side fallback. The change should therefore keep one shared problem statement while treating those two tracks as independent evidence during exploration and validation.

Alternative considered:
- Keep the old Prompt B menu-and-selection task as the second primary baseline. Rejected because the manual control probe showed that the basic compile-and-call path is cleaner than the old Prompt B evidence implies, so the old task would confound mainline diagnosis.

### Decision: Introduce a new named baseline prompt for basic C# compile-and-call verification
The baseline validation set should add a new named standard prompt, tentatively "Standard Prompt C: Basic C# Compile And Call", instead of mutating the archived wording of Prompt B. This keeps historical comparability intact while creating a cleaner target for the current mainline change.

The new track should ask the validating agent to:

- write a minimal C# static function into the host project
- complete any needed compile recovery through the CLI
- verify through the CLI that a later JS `exec` call can invoke that function and observe the correct returned value

Alternative considered:
- Rewrite the old Prompt B wording in place. Rejected because the archived task-prompt rules explicitly say future task variants should be added as new named standard prompts instead of mutating Prompt A or Prompt B.

### Decision: Explore contract and workflow shape before implementation
The repository already exposes multiple observation and recovery surfaces, and the manual control probe showed that not every compile-adjacent workflow is broken. The next productive step is therefore to inspect whether the remaining gap is missing capability, poor composition, insufficient guidance, or simply a baseline task that had become too confounded. This change should explicitly reserve early tasks for problem decomposition and option comparison before any implementation work is proposed.

Alternative considered:
- Start implementing a guessed verification helper immediately. Rejected because the current evidence still allows multiple different root causes.

### Decision: Prompt A should treat slow project-scoped startup as an accepted exec lifecycle
For the Prompt A class of workflow, the preferred product behavior is that `exec --project-path ...` becomes the clear primary path even when Unity startup or recovery is slow. If the CLI has already taken ownership of the project-scoped startup or recovery flow for the exec request, it should prefer returning a non-terminal accepted state such as `running` with a stable `request_id`, rather than a terminal-looking startup failure that pushes the caller into ad hoc diagnosis.

The returned payload should also include a default follow-up hint that is explicit enough for medium-capability agents to use directly, including a complete recommended `wait-for-exec` argv. A future quieting flag may suppress these hints for callers that want to minimize output volume, but the default behavior should bias toward agent-friendly continuity.

The current runtime shape makes this gap concrete: project-scoped `exec` still calls readiness establishment before it submits the request to the execution service. In practice, that means a slow startup can still fail before the request enters the accepted request lifecycle at all. The desired change is therefore not just wording; it is a contract shift in where the accepted boundary sits for project-scoped `exec`.

Alternative considered:
- Continue treating slow startup as a plain exec failure and expect the caller to switch to `wait-until-ready`. Rejected because it makes the nominal work command look terminal too early and turns a normal project-scoped exec path into a two-command recovery dance.

### Decision: Wait-for-exec continues one request lifecycle, not cross-session recovery
The Prompt A improvement should expand `wait-for-exec` to cover a broader portion of the same request lifecycle, including startup, readiness recovery, and compile-time waiting when the original request remains valid. It should not, however, imply cross-session or cross-runtime resurrection. If session replacement, runtime loss, or script-reload invalidation breaks the original request identity, `wait-for-exec` should fail explicitly rather than pretending the original request can continue across that boundary.

Alternative considered:
- Treat `wait-for-exec` as a generic recovery command that can span session replacement or post-compilation request invalidation. Rejected because it would blur the request contract and create false expectations about what `request_id` continuity means.

### Decision: Prompt A contract should define an explicit project-scoped accepted boundary and continuation payload
For Prompt A, the contract should be concrete enough that later implementation work can be judged against explicit payload expectations. The intended boundary is:

- if the CLI has accepted responsibility for starting or recovering Unity for the addressed project in order to run the request, the response should already be inside the accepted request lifecycle
- a slow-but-still-progressing project startup should therefore prefer `status = "running"` plus a stable `request_id`
- only unrecoverable startup outcomes, such as Unity truly exiting or launch ownership failing, should remain terminal startup failures

The accepted response for this Prompt A class should also expose an explicit continuation payload, with the default form being a full recommended `wait-for-exec` argv rather than a vague textual hint.

That means the desired payload shape is conceptually closer to:

- `status = "running"`
- top-level `request_id`
- a top-level continuation payload that points to `wait-for-exec --project-path ... --request-id ...`

without implying that the request can survive session replacement or post-reload invalidation.

The continuation payload should stay small and fit the current machine-readable response style. The current CLI already uses top-level fields such as `status`, `request_id`, `result`, and optional `log_offset`, so the continuation hint should be a sibling field rather than part of script-authored `result`. A minimal target shape is:

- `next_step.command`: the preferred follow-up command id, initially `wait-for-exec`
- `next_step.argv`: the full recommended argv, including selector and `request_id`
- optional short descriptive text only if it does not displace the machine-usable argv as the primary value

The default should favor explicit argv because medium-capability agents often follow a concrete command more reliably than a prose-only recommendation.

Alternative considered:
- Leave the accepted boundary implicit and only improve help prose. Rejected because the current failure mode happens before the caller ever receives an accepted request identity to follow, so help alone would not close the gap.

### Decision: Basic compile-and-call verification should prefer direct exec-result closure over log observation
For the new Standard Prompt C track, the preferred baseline verification path should be:

- write the C# change through `exec`
- let the project-scoped lifecycle absorb any necessary refresh and compile wait
- issue a later `exec` that calls the new C# method
- confirm success from the returned CLI `result`

This track should not depend on result-marker or log-pattern observation unless new evidence shows the simple compile-and-call path is insufficient.

Alternative considered:
- Continue using a log-oriented baseline to represent all post-compile verification. Rejected because the direct compile-and-call control probe already demonstrates a cleaner baseline that avoids unrelated editor timing and observation-surface complexity.

### Decision: Accept limited bridge-shape dependency in Standard Prompt C, but record it explicitly
Standard Prompt C is still not a pure compile-only task because the final verification step requires a JS-side call into the newly written C# code. The current published help appears to expose the required bridge shape only indirectly through examples such as `puer.loadType(...)`, not as a dedicated bridge reference section. That means Standard Prompt C still carries some bridge discoverability noise, but materially less than the old menu-and-selection task.

The mainline change should therefore keep Standard Prompt C as the cleaner baseline while recording this residual risk explicitly instead of pretending the task is bridge-free.

Alternative considered:
- Reject Standard Prompt C until bridge access is documented more formally. Rejected because the current goal is to isolate the larger verification and editor-timing confounds first, not to wait for a perfect bridge-specific prompt.

### Decision: Standard Prompt C should gain an explicit compile-recovery option on `exec`
The latest rerun showed that Standard Prompt C can stay inside the CLI surface for final verification, but it still reaches `recoverable` because the agent must manually force `AssetDatabase.Refresh()` and `CompilationPipeline.RequestScriptCompilation()`, then call `wait-until-ready`, before the newly written type becomes callable. That extra sequence is too low-level for a basic validation rail and should be expressible as one project-scoped `exec` option instead of a separate manual dance.

The preferred next slice is to add an explicit flag on project-scoped `exec`, tentatively `--refresh-before-exec`, with this intent:

- refresh the addressed Unity project before running the requested script
- if the refresh enters a compile or readiness-recovery window, keep that work inside the same request lifecycle
- once Unity is ready again, execute the requested script content
- if the whole flow takes longer than the current wait budget, return `running + request_id` and let `wait-for-exec` continue the same request

This keeps the caller's mental model aligned with the existing `exec` primary path:

- the caller still asks to do the next task step through `exec`
- refresh and compile recovery become an execution precondition, not a separate workflow to orchestrate manually
- `wait-until-ready` remains a supporting command rather than the default compile-recovery tool between every task step

The first version should stay explicit rather than automatic. Not every `exec` warrants a refresh pass, and making this behavior implicit for all project-scoped execution would add latency and make ordinary script calls heavier than necessary.

Alternative considered:
- Add a standalone `refresh-project` command first. Rejected for the mainline path because it would create another orchestration step for the caller and weaken the existing `exec -> running -> wait-for-exec` request model.

### Decision: First compile-recovery experiment favors `AssetDatabase.Refresh()` without mandatory `RequestScriptCompilation()`
A direct control experiment after the rerun narrowed the next contract step further. In that probe:

- a new C# file was added to `Assets/__AgentValidation`
- the new type was initially absent from loaded assemblies
- a project-scoped `exec` that only called `AssetDatabase.Refresh()` completed successfully
- the immediately following `exec` could already resolve and invoke the new type without a manual `CompilationPipeline.RequestScriptCompilation()` step and without an intermediate caller-authored `wait-until-ready`

This means the first contract version for `--refresh-before-exec` should be conservative:

- treat project refresh as the required action
- do not make explicit `RequestScriptCompilation()` part of the default promised behavior
- if refresh causes Unity to enter a longer import or compile window, keep that wait inside the same request lifecycle and surface it through the normal `running + request_id -> wait-for-exec` path
- if refresh does not push Unity into a not-ready window, continue directly into the requested script execution without adding an artificial extra wait

The same experiment also suggests a small diagnostics improvement: when `exec` is still in progress because of this pre-execution refresh step, the machine-readable response should expose that the request is currently in a refresh-related phase. That phase detail is primarily for diagnosis and should not change the top-level `running` contract.

Alternative considered:
- Bake `CompilationPipeline.RequestScriptCompilation()` into the default first version. Rejected for now because the control probe did not require it, so making it mandatory would over-specify the heavier path before evidence justifies it.

### Decision: Define validation quality in terms of CLI-native closure, not task success alone
This change needs explicit acceptance semantics so later reruns do not collapse all successful tasks into one bucket. The working meaning should be:

- `clean`: the agent completes the task and confirms success through the intended CLI surface without host-side fallback and without an additional recovery dance that the current mainline change is specifically trying to eliminate.
- `recoverable`: the agent completes the task autonomously but needs extra recovery, probing, or non-primary CLI branching before it can finish verification within the CLI surface.
- `fallback`: the agent completes or nearly completes the task only after leaving the intended CLI verification surface, for example by relying on direct host-file or host-log inspection for final confirmation.

Applied to the current two acceptance tracks, that means:

- Prompt A reaches `clean` only when project-scoped `exec` startup continuity is good enough that the agent can stay on the primary request lifecycle and confirm the scene outcome through CLI-native verification.
- Standard Prompt C reaches `clean` when the agent can write the C# method, let normal compile recovery happen through the CLI path, and confirm the later call result from CLI output without host-side inspection.

Alternative considered:
- Keep only qualitative prose in validation summaries. Rejected because the current change needs sharper acceptance boundaries before implementation choices can be judged coherently.

### Decision: Implement Prompt A continuity first and use Standard Prompt C as the first guardrail rerun
The first implementation slice for this change should target Prompt A, because its remaining gap is now concrete at the contract and runtime-boundary level:

- project-scoped `exec` currently establishes readiness before the request is accepted
- this creates terminal-looking startup failure before `request_id` continuity exists
- the desired fix is specific enough to implement and validate

Standard Prompt C should remain part of the same change, but primarily as the cleaner baseline rerun that checks whether verification closure stays inside the CLI surface after Prompt A-oriented work lands. If Standard Prompt C later exposes a separate bridge or compile-contract problem, that can still justify a second implementation slice, but it should not block the first one.

The first rerun protocol should therefore stay narrow:

- rerun Prompt A first
- rerun Standard Prompt C second
- keep the same fixed subagent model
- preserve the help-only discovery restriction
- record `clean`, `recoverable`, or `fallback` separately for both tracks

That rerun is meant to answer a focused question: did the Prompt A continuity slice improve the primary request lifecycle without regressing the cleaner compile-and-call verification rail?

Alternative considered:
- Try to implement Prompt A and Standard Prompt C improvements together as one broad runtime patch. Rejected because Prompt A already provides a sharply defined first slice, while Standard Prompt C is currently more useful as a regression guardrail than as a separate runtime mechanism.

### Decision: Use compile recovery on `exec` as the second implementation slice
After the Prompt A continuity slice and rerun, the next implementation target should be the Standard Prompt C compile-recovery path. The immediate objective is not to solve every code-import edge case, but to remove the low-level manual sequence where an agent must explicitly force refresh, request script compilation, and then separately wait for readiness before attempting the real verification call.

The second rerun protocol should therefore focus on:

- whether Standard Prompt C can move from `recoverable` toward `clean` when project-scoped `exec` is allowed to refresh before the verification step
- whether the extra compile-recovery support preserves the Prompt A gains rather than regressing the accepted request lifecycle
- whether refresh-phase reporting is informative enough to diagnose slow or abnormal pre-execution import windows without introducing a new top-level status family

Alternative considered:
- Leave Standard Prompt C as permanently recoverable and handle compile recovery only through user-authored scripts. Rejected because the current manual compile dance is exactly the kind of agent-hostile orchestration the mainline verification-closure change is trying to reduce.

### Decision: Keep refresh-phase reporting small and sibling to the top-level status
The compile-recovery slice should expose refresh progress in a machine-readable way without introducing a new top-level status family. The smallest useful contract is:

- keep `status = "running"` as the top-level lifecycle signal
- add a sibling `phase` field when the request is still progressing through a known pre-execution stage
- require the first version to support at least `phase = "refreshing"` and `phase = "executing"`

The primary reason for the field is diagnosis. A caller that sees `running` should still continue with the same `wait-for-exec` behavior regardless of phase, but the extra field makes it easier to distinguish a slow refresh/import window from actual script execution time.

The first version does not need to promise a distinct `phase = "compiling"` state unless implementation evidence shows that this stage can be surfaced reliably without adding confusion or churn to the contract.

Alternative considered:
- Introduce new top-level statuses such as `refreshing` or `compiling`. Rejected because the caller already has a stable continuation model based on `running`, and fragmenting that model would make the API heavier for limited diagnostic gain.

### Decision: Compile-phase responses should join the same `running` continuation model
The second-slice rerun narrowed the remaining Prompt C gap further. The validating agent naturally discovered and used `--refresh-before-exec`, which means the main product-entry problem is solved. The remaining friction is what happens after the first refreshed verification attempt returns a compile-phase response. Today that response is still surfaced as `status = "compiling"` by the underlying execution service, which leaves the caller without the same continuation affordances that exist for `running`.

The next contract step should therefore normalize this phase into the same outer request model:

- the caller-facing response should remain on `status = "running"`
- the response should expose `phase = "compiling"`
- the same top-level `request_id` and `next_step` continuation contract should apply
- `wait-for-exec` should continue to own this compile-recovery portion of the lifecycle instead of pushing the caller toward a separate `wait-until-ready` branch

This keeps the product model coherent:

- `wait-until-ready` remains a supporting readiness tool
- `wait-for-exec` remains the canonical continuation path for an already accepted request
- compile recovery after `--refresh-before-exec` becomes part of that same accepted request lifecycle

Alternative considered:
- Keep surfacing compile as a separate top-level `compiling` status and let callers branch to `wait-until-ready`. Rejected because the rerun shows this is now the main remaining source of recoverable extra work in Prompt C.

## Risks / Trade-offs

- [The common root-cause hypothesis may still be wrong] → Keep Prompt A and Standard Prompt C acceptance separate so a later split remains easy if the evidence diverges.
- [The change may stay abstract for too long] → Make the early tasks produce concrete problem decomposition and candidate solution comparisons, not only general discussion.
- [Verification closure may depend on startup behavior more than expected] → Reassess scope during exploration and open or link a dedicated startup-focused follow-up if needed.
- [The new baseline may underrepresent harder verification cases] → Keep the linked log-observation and editor-interaction changes active so those harder cases are not forgotten, only deferred out of the mainline baseline.
- [Standard Prompt C still depends on implicit bridge discoverability] → Record that residual noise explicitly and reassess later whether bridge usage needs its own help-focused follow-up.
