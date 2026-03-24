# agent-cli-discoverability-validation Specification

## Purpose
Define the repository-owned validation protocol and evidence expectations for measuring whether AI agents can discover, recover, and complete representative Unity workflows through the published `unity-puer-exec` CLI surface without repository-only guidance.
## Requirements
### Requirement: Help-only agent validation uses published CLI discovery surfaces
The repository SHALL define a repeatable validation protocol for agent CLI discoverability that restricts the primary discovery surface to the publishable `unity-puer-exec` help interface and normal CLI execution.

#### Scenario: Contributor prepares a help-only agent trial
- **WHEN** a contributor runs the repository-owned agent discoverability validation
- **THEN** the protocol allows `unity-puer-exec --help`, command help, `--help-args`, `--help-status`, `--help-example`, and normal CLI execution
- **AND** the protocol does not rely on repository-only source or repository tests as part of the allowed discovery surface

### Requirement: First-round validation covers both simple and multi-step Unity Editor tasks
The repository SHALL define an initial task set that exercises both direct Unity Editor action and a longer workflow that includes code change, compile or readiness recovery, and outcome verification.

#### Scenario: Contributor reviews the first-round task set
- **WHEN** the first-round help-only validation tasks are defined
- **THEN** the task set includes at least one simple Unity Editor action task
- **AND** the task set includes at least one longer workflow task that requires the agent to complete a code change and verify the result in the real editor context

### Requirement: Validation records success, autonomy, and efficiency separately

The repository SHALL record task outcome, allowed-surface compliance, and convergence quality as distinct findings so discoverability problems can be diagnosed without collapsing all failures into one score. Each recorded task result SHALL also retain durable transcript evidence that includes the task prompt, the help surface consulted, the key command sequence, and the key outputs used to judge the result. When a validation task creates repository-owned temporary assets in the external host Unity project, the recorded result SHALL also include cleanup outcome and any remaining residue.

#### Scenario: Contributor records a task result
- **WHEN** a help-only validation task finishes
- **THEN** the recorded result includes whether the intended Unity-side outcome was achieved
- **AND** the recorded result includes whether the agent stayed within the allowed discovery boundary
- **AND** the recorded result includes an efficiency assessment that distinguishes clean convergence from recoverable or poor trial-and-error
- **AND** the recorded result retains durable transcript evidence for later review
- **AND** the recorded result includes cleanup status for any repository-owned temporary host assets created by the run

### Requirement: Validation findings isolate discoverability gaps
The repository SHALL capture concrete discoverability findings from each help-only trial in a form that can drive later product, workflow, or harness follow-up work.

#### Scenario: Contributor summarizes a help-only trial
- **WHEN** a help-only agent validation run is reviewed
- **THEN** the summary identifies the help or workflow gaps that materially slowed or blocked the task
- **AND** the summary distinguishes those discoverability findings from unrelated runtime or environment failures

### Requirement: Validation transcript records preserve key agent behavior
The repository SHALL define a minimum transcript record for each help-only agent validation run so later reviewers can reconstruct how the agent discovered and used the CLI.

#### Scenario: Contributor stores transcript evidence for a validation run
- **WHEN** a help-only validation run is recorded
- **THEN** the stored evidence includes the task prompt or prompt identifier
- **AND** the stored evidence includes the model or agent label used for the run
- **AND** the stored evidence includes the discovery constraints that applied to the run
- **AND** the stored evidence includes the key help commands consulted by the agent
- **AND** the stored evidence includes the key CLI command sequence and the outputs that justified the recorded outcome
- **AND** the stored evidence includes distinct result fields for task success, autonomy, efficiency, and cleanup status
- **AND** the stored evidence includes concrete discoverability findings for later follow-up work

### Requirement: Validation transcript records explicit operator observations
The repository SHALL record operator-observed intervention and Unity-native modal blockers separately from the agent command trace so reviewers can distinguish discoverability issues from external interference.

#### Scenario: Contributor records a run affected by observation or intervention
- **WHEN** a help-only validation run is recorded
- **THEN** the transcript record includes whether the operator only observed the run or performed non-decisive or decisive intervention
- **AND** the transcript record includes whether a Unity-native modal blocker was observed
- **AND** the transcript record identifies how the blocker was detected and how it was resolved when known

### Requirement: Validation transcript storage separates durable summaries from transient raw logs
The repository SHALL allow long raw transcript logs to live outside OpenSpec while still requiring a durable structured record that remains useful after temporary logs expire.

#### Scenario: Contributor stores transcript artifacts for a validation run
- **WHEN** a help-only validation run is recorded
- **THEN** the durable change or spec-owned record preserves the minimum structured transcript fields
- **AND** long raw logs may be stored under `.tmp/agent-validation-transcripts/`
- **AND** the durable record points to any retained raw transcript location when such evidence exists

### Requirement: Help efficiency validation compares convergence quality across revisions
The repository SHALL treat agent-efficiency validation as a comparison problem, using transcript-backed evidence to assess whether help revisions reduce unnecessary exploration for representative tasks.

#### Scenario: Contributor evaluates a help efficiency change
- **WHEN** a contributor reruns representative help-only agent validation tasks after a help-surface change
- **THEN** the evaluation compares convergence quality against earlier transcript-backed runs
- **AND** the evaluation does not rely only on final task success as the measure of improvement

### Requirement: Bridge-recognition validation records probing separately
The repository SHALL record bridge-recognition-specific probing separately from other workflow friction when evaluating help-only agent runs that require JavaScript-to-C# interaction.

#### Scenario: Contributor reviews a bridge-sensitive validation run
- **WHEN** a help-only validation run requires the agent to call Unity or C# APIs from JavaScript
- **THEN** the durable record states whether the agent needed extra bridge-shape probing before the main task converged
- **AND** the record distinguishes that probing from compile recovery, startup continuity, and persistence-confirmation behavior

### Requirement: Bridge-guidance validation measures first-pass bridge recognition
The repository SHALL evaluate bridge-guidance changes partly by whether representative tasks reach correct bridge usage with less exploratory probing than earlier transcript-backed runs.

#### Scenario: Contributor reruns Prompt A or Standard Prompt C after a bridge-guidance change
- **WHEN** a contributor compares a new bridge-guidance validation run against earlier durable records
- **THEN** the evaluation states whether the agent formed the intended PuerTS-style bridge model earlier in the run
- **AND** the evaluation states whether the first serious verification attempt already used the intended bridge shape
- **AND** final task success alone is not treated as sufficient evidence of bridge-guidance improvement

### Requirement: Bridge-guidance validation records bridge-specific help usage
The repository SHALL record which published help surfaces the agent used to discover bridge behavior when that behavior is relevant to the task.

#### Scenario: Contributor stores transcript evidence for a bridge-oriented validation run
- **WHEN** a help-only validation run depends on bridge guidance
- **THEN** the durable record includes the bridge-relevant help commands or examples the agent consulted
- **AND** the record can show whether the agent relied on a purpose-built bridge help path or inferred bridge usage from unrelated examples

### Requirement: Baseline validation records whether verification stayed inside the CLI surface
The repository SHALL record whether each baseline help-only agent workflow completed verification through the intended CLI observation surface or relied on host-side fallback confirmation. This distinction SHALL be recorded even when task success, autonomy, and efficiency are otherwise acceptable.

#### Scenario: Contributor records a baseline workflow result
- **WHEN** a baseline help-only validation run finishes
- **THEN** the durable record states whether final confirmation stayed inside the CLI surface
- **AND** any host-file or host-log fallback used for final confirmation is identified explicitly

### Requirement: Verification-closure evaluation uses explicit convergence classes
The repository SHALL evaluate verification-closure changes with explicit convergence classes so later reruns can distinguish clean CLI-native closure from autonomous-but-recoverable execution and from host-side fallback.

#### Scenario: Contributor classifies a verification-oriented baseline run
- **WHEN** a contributor records the result of Prompt A or Standard Prompt C after a verification-oriented change
- **THEN** the durable record classifies the run as `clean`, `recoverable`, or `fallback`
- **AND** `clean` means the task converged and verified through the intended CLI surface without host-side fallback
- **AND** `recoverable` means the task still converged autonomously but needed extra recovery or probing before CLI-native verification succeeded
- **AND** `fallback` means final confirmation depended on direct host-file or host-log inspection outside the intended CLI surface

### Requirement: Verification-closure evaluation tracks Prompt A and Standard Prompt C separately
The repository SHALL evaluate verification-closure improvements against Prompt A and a separate named baseline for basic C# compile-and-call validation so shared fixes can still be judged against distinct startup and compile-verification friction patterns.

#### Scenario: Contributor evaluates a verification-closure change
- **WHEN** a contributor reruns the baseline help-only validation after a verification-oriented CLI change
- **THEN** the evaluation reports Prompt A and Standard Prompt C outcomes separately
- **AND** the summary states whether each workflow achieved clean CLI-native verification, recoverable verification, or host-side fallback

### Requirement: New baseline prompt variants preserve archived prompt stability
The repository SHALL add future baseline workflow variants as new named standard prompts rather than mutating the archived wording of Prompt A or Prompt B.

#### Scenario: Contributor introduces a cleaner baseline task
- **WHEN** a contributor decides that the existing Prompt B task is no longer the right mainline baseline for a specific verification-closure investigation
- **THEN** the contributor defines a new named standard prompt for that cleaner baseline
- **AND** the archived Prompt A and Prompt B wording remains unchanged for historical comparability

### Requirement: Basic-workflow revalidation preserves the comparison anchor
The repository SHALL treat basic-workflow CLI revalidation as a comparison exercise that preserves the original baseline inputs. A revalidation round for the baseline workflows SHALL reuse the existing Prompt A and Prompt B goal wording, SHALL keep the validating model fixed when comparability is the goal, and SHALL avoid execution patterns that introduce known shared-project contention into the authoritative evidence.

#### Scenario: Contributor prepares a baseline revalidation round
- **WHEN** a contributor reruns the repository's baseline help-only workflow validation to compare the current CLI against earlier evidence
- **THEN** the round reuses the existing Prompt A and Prompt B wording apart from concrete path substitution
- **AND** the round records the validating model identity explicitly
- **AND** the authoritative evidence does not rely on parallel runs that contend against the same Unity project state

### Requirement: Basic-workflow revalidation scores environment friction as product-facing outcome
The repository SHALL evaluate baseline help-only workflow results with environment friction included in the product-facing outcome when that friction materially affects autonomous CLI use. Readiness recovery, compile timing, observation timing, launch contention, modal handling, and similar workflow obstacles SHALL contribute to the recorded assessment when they force additional agent recovery work, reduce autonomy, or block completion.

#### Scenario: Contributor reviews a revalidation result with workflow friction
- **WHEN** a baseline help-only validation run encounters real workflow friction while using the published CLI surface
- **THEN** the recorded findings identify that friction explicitly
- **AND** the final assessment treats the friction as part of the evaluated CLI effectiveness rather than dismissing it as out of scope
- **AND** operator observation or blocker notes remain recorded separately so reviewers can still distinguish agent behavior from external facts

### Requirement: Ordinary log-workflow guidance is validated against transcript-backed reruns
The repository SHALL evaluate ordinary log-workflow help changes with a clean help-only rerun of the representative log-oriented baseline so the effect of the published workflow example can be judged against prior transcript-backed evidence.

#### Scenario: Contributor reruns the representative log-oriented baseline
- **WHEN** a contributor validates a help-surface change that adds or revises the ordinary log workflow example
- **THEN** the contributor runs a help-only trial that reuses the representative log-oriented baseline rather than relying only on unit tests or implementation-session notes
- **AND** the resulting record compares the rerun against earlier transcript-backed Prompt B style evidence

### Requirement: Ordinary log-workflow reruns record final verification path explicitly
The repository SHALL record whether a representative log-oriented rerun kept final confirmation inside the CLI observation surface or fell back to direct host-log inspection.

#### Scenario: Contributor records the rerun outcome
- **WHEN** the representative log-oriented help-only rerun finishes
- **THEN** the durable record states whether final confirmation used the intended CLI observation path
- **AND** the durable record states whether direct host-log inspection was still used for final verification
- **AND** those findings are recorded separately from unrelated compile recovery or startup friction

### Requirement: Ordinary log-workflow reruns record checkpoint usage explicitly
The repository SHALL record whether a representative log-oriented rerun used the intended observation checkpoint pattern when validating ordinary log-workflow guidance.

#### Scenario: Contributor summarizes checkpoint usage
- **WHEN** a contributor reviews a representative log-oriented help-only rerun after the ordinary log workflow example change
- **THEN** the durable record states whether the run captured `log_offset` before calling `wait-for-log-pattern`
- **AND** the durable record states whether `wait-for-log-pattern` started from the returned checkpoint
- **AND** the durable record distinguishes checkpoint-usage findings from unrelated runtime or environment issues

