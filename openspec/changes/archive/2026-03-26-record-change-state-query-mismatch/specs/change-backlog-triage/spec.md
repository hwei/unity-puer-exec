## MODIFIED Requirements

### Requirement: Change-query output distinguishes raw metadata from interpreted state
Repository query tooling SHALL preserve access to a change's raw `meta.yaml` planning state while also surfacing an interpreted operator-facing state when dependency resolution, archived prerequisites, generic OpenSpec workflow reporting, or abnormal repository state make raw metadata alone insufficient for trustworthy planning decisions.

#### Scenario: Query output detects a state interpretation gap
- **WHEN** a maintainer or agent queries a non-archived change whose raw metadata does not cleanly match the effective planning situation
- **THEN** the query surface reports enough information to distinguish raw metadata from the interpreted operator-facing state
- **AND** the output does not silently force contributors to infer which source of truth to trust

#### Scenario: Raw metadata and generic workflow state disagree
- **WHEN** a non-archived change still carries raw metadata such as `status: queued` while a generic OpenSpec workflow surface reports the same change as workflow `in-progress`
- **THEN** repository query behavior preserves visibility into both the raw metadata state and the workflow interpretation
- **AND** the mismatch is presented as an explicit diagnostic condition rather than as an unexplained contradiction
