## MODIFIED Requirements

### Requirement: exec and wait-for-exec responses include log_range and brief_sequence

Every `exec` and `wait-for-exec` response SHALL include a top-level `log_range` object with `start` and `end` offset fields, and a top-level `brief_sequence` string. `log_range.start` SHALL be set to the log position at the time the CLI began observing the log for the request. `log_range.end` SHALL be set to the latest observed log tail at response time and SHALL never be absent. `brief_sequence` SHALL use a compact run encoding where each brief kind still uses the existing symbols (`"I"`, `"W"`, `"E"`, `"?"`), single-entry runs are emitted as the bare symbol, and repeated runs append a decimal count to the symbol. For example, `WI32E2I` represents `W`, then thirty-two `I` briefs, then two `E` briefs, then one `I` brief.

#### Scenario: exec returns with repeated log activity during the operation

- **WHEN** `exec` returns any status response with long repeated runs of the same brief kind
- **THEN** the response includes `log_range.start`, `log_range.end`, and compact encoded `brief_sequence`
- **AND** callers can still reconstruct the underlying brief kinds from the encoded form without ambiguity
