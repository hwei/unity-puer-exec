## ADDED Requirements

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
