## ADDED Requirements

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
