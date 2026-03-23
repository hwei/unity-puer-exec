## ADDED Requirements

### Requirement: Fragile editor-interaction scenarios can remain deferred validation tracks
The repository SHALL allow fragile Unity Editor interaction scenarios to remain as deferred validation tracks when they are valuable for later coverage but currently too entangled with editor timing behavior to serve as the main core-workflow baseline.

#### Scenario: Contributor stages a fragile editor-interaction task for later validation
- **WHEN** a validation scenario is still useful but currently mixes core CLI workflow quality with Unity Editor interaction timing traps
- **THEN** the repository may preserve that scenario as a deferred validation track
- **AND** the record identifies the earlier changes or investigations it depends on before rerun
