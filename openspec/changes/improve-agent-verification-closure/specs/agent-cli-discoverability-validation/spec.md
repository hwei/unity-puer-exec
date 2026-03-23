## ADDED Requirements

### Requirement: Baseline validation records whether verification stayed inside the CLI surface
The repository SHALL record whether each baseline help-only agent workflow completed verification through the intended CLI observation surface or relied on host-side fallback confirmation. This distinction SHALL be recorded even when task success, autonomy, and efficiency are otherwise acceptable.

#### Scenario: Contributor records a baseline workflow result
- **WHEN** a baseline help-only validation run finishes
- **THEN** the durable record states whether final confirmation stayed inside the CLI surface
- **AND** any host-file or host-log fallback used for final confirmation is identified explicitly

### Requirement: Verification-closure evaluation tracks Prompt A and Prompt B separately
The repository SHALL evaluate verification-closure improvements against Prompt A and Prompt B separately so shared fixes can still be judged against the distinct friction patterns of the simple and multi-step workflows.

#### Scenario: Contributor evaluates a verification-closure change
- **WHEN** a contributor reruns the baseline help-only validation after a verification-oriented CLI change
- **THEN** the evaluation reports Prompt A and Prompt B outcomes separately
- **AND** the summary states whether each workflow achieved clean CLI-native verification, recoverable verification, or host-side fallback
