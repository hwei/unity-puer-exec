## ADDED Requirements

### Requirement: Local release preparation preserves the existing CI publish trigger
The repository SHALL keep `v<version>` source tag push as the event that triggers the GitHub Actions OpenUPM publish workflow, even when a local release helper is used to prepare the source release beforehand.

#### Scenario: Maintainer finishes local release preparation
- **WHEN** a maintainer completes release preparation with the local helper
- **THEN** the repository still requires an explicit remote push of the source commit and `v<version>` tag to trigger publishing
- **AND** the local helper does not itself publish to OpenUPM or replace the existing CI release workflow
