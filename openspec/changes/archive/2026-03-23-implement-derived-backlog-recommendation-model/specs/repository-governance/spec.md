## MODIFIED Requirements

### Requirement: Superseded changes are archived rather than deleted
Changes that are no longer the recommended execution path SHALL be marked superseded only as a temporary pre-archive disposition rather than as a normal long-lived planning state. Once their disposition is clear, superseded changes SHALL be archived so they no longer appear in active planning scans, typically without updating main specs when no durable requirement change is being merged.

#### Scenario: Older change is replaced by newer direction
- **WHEN** a maintainer decides that an existing non-archived change has been replaced by a newer change or conclusion
- **THEN** the older change may be marked superseded as a temporary disposition
- **AND** the older change is archived once its disposition is stable
- **AND** the repository keeps the archived record instead of deleting the change from history

#### Scenario: Superseded change lingers in active scans
- **WHEN** a non-archived change remains marked superseded instead of being archived promptly
- **THEN** repository workflow treats that state as archive hygiene debt rather than as a normal steady-state planning bucket
- **AND** maintainers can identify the change as requiring cleanup
