## ADDED Requirements

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
