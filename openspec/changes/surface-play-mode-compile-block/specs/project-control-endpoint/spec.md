## MODIFIED Requirements

### Requirement: Health response exposes whether automatic refresh is currently suppressed

The health endpoint SHALL report when automatic refresh is suppressed because the Editor is in play mode, together with the reason. A caller SHALL be able to observe that a pending change will not be refreshed until play mode exits. While suppression is reported, the health response SHALL also report the Editor's "Script Changes While Playing" preference, so a caller can tell whether Unity itself would compile during play.

#### Scenario: Editor is in play mode with a pending change

- **WHEN** a caller probes `/health` while the Editor is in play mode
- **AND** a compile-triggering change is pending
- **THEN** the health response reports that refresh is suppressed
- **AND** it reports play mode as the reason

#### Scenario: Health reports the Script Changes While Playing preference

- **WHEN** a caller probes `/health` while the Editor is in play mode
- **THEN** the suppression block reports the preference as one of `recompile_and_continue_playing`, `recompile_after_finished_playing`, or `stop_playing_and_recompile`
- **AND** it reports `unknown` when the preference cannot be read

#### Scenario: Editor is not in play mode

- **WHEN** a caller probes `/health` while the Editor is not in play mode
- **THEN** the health response does not report refresh as suppressed for that reason
